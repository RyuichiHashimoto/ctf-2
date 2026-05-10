"""パイプライン実行時のメトリクス収集。

新しいメトリクスを追加する手順:
  - 単純な値: pipeline.py から metrics.set("key", value) を呼ぶだけでよい
  - 構造化された計測: このファイルに record_xxx() メソッドを追加する
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from libs.attack_graph_lib.schema import GraphData


@dataclass
class MetricsCollector:
    """1回の実行におけるメトリクスを収集する。

    Attributes
    ----------
    started_at : float
        計測開始時刻（``time.perf_counter`` の値）。
    values : dict of {str: Any}
        収集したメトリクス値。
    """

    started_at: float = field(default_factory=perf_counter)
    values: dict[str, Any] = field(default_factory=dict)

    def record_graph(self, prefix: str, graph: GraphData) -> None:
        """グラフのノード数とエッジ数を記録する。

        Parameters
        ----------
        prefix : str
            メトリクス名の接頭辞。``{prefix}_nodes`` と ``{prefix}_edges``
            として保存する。
        graph : GraphData
            記録対象のグラフ。
        """
        self.values[f"{prefix}_nodes"] = len(graph.nodes)
        self.values[f"{prefix}_edges"] = len(graph.edges)

    def set(self, key: str, value: Any) -> None:
        """任意のメトリクス値を記録する。

        Parameters
        ----------
        key : str
            メトリクス名。
        value : Any
            記録する値。
        """
        self.values[key] = value

    def snapshot(self) -> dict[str, Any]:
        """収集済みメトリクスのスナップショットを返す。

        Returns
        -------
        dict of {str: Any}
            収集済みメトリクスに経過秒数（``elapsed_seconds``）を加えた辞書。
        """
        return {**self.values, "elapsed_seconds": perf_counter() - self.started_at}
