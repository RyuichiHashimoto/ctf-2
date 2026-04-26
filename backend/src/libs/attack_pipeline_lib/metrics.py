"""パイプライン実行時のメトリクス収集。"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from libs.attack_graph_lib.schema import GraphData


@dataclass
class MetricsCollector:
    """1回の実行におけるメトリクスを収集する。

    Attributes:
        started_at: 計測開始時刻。
        values: 収集したメトリクス値。
    """

    started_at: float = field(default_factory=perf_counter)
    values: dict[str, Any] = field(default_factory=dict)

    def record_graph(self, prefix: str, graph: GraphData) -> None:
        """グラフのノード数とエッジ数を記録する。

        Args:
            prefix: メトリクス名の接頭辞。
            graph: 記録対象のグラフ。
        """
        self.values[f"{prefix}_nodes"] = len(graph.nodes)
        self.values[f"{prefix}_edges"] = len(graph.edges)

    def set(self, key: str, value: Any) -> None:
        """任意のメトリクス値を記録する。

        Args:
            key: メトリクス名。
            value: 記録する値。
        """
        self.values[key] = value

    def snapshot(self) -> dict[str, Any]:
        """収集済みメトリクスのスナップショットを返す。

        Returns:
            収集済みメトリクスに経過秒数を加えた辞書。
        """
        return {**self.values, "elapsed_seconds": perf_counter() - self.started_at}
