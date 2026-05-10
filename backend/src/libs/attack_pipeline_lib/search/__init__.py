"""攻撃経路探索アルゴリズムのインターフェースと実装。

新しい探索アルゴリズムを追加する手順:
  1. このフォルダに新しいファイルを追加する (例: search/topk_shortest.py)
  2. PathSearcher を満たすクラスを実装する
  3. pipeline.py の _build_searcher() に選択肢として登録する
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from libs.attack_graph_lib.schema import GraphData

from .exhaustive import ExhaustiveSearcher


@runtime_checkable
class PathSearcher(Protocol):
    """経路探索アルゴリズムのインターフェース。

    新しいアルゴリズムを実装する場合は、このプロトコルに準拠したクラスを
    ``search/`` 配下のファイルに定義する。

    Methods
    -------
    search(graph, start_node, target_nodes, attack_scenario, max_nodes)
        指定された開始ノードから終了ノード群への攻撃経路を探索する。
    """

    def search(
        self,
        graph: GraphData,
        start_node: str,
        target_nodes: set[str],
        attack_scenario: list[str] | None,
        max_nodes: int,
    ) -> list[dict[str, Any]]:
        """指定された開始ノードから終了ノード群への攻撃経路を探索する。

        Parameters
        ----------
        graph : GraphData
            探索対象のシステム構成グラフ。
        start_node : str
            攻撃の開始ノードID。
        target_nodes : set of str
            攻撃の終了候補ノードIDの集合。
        attack_scenario : list of str or None
            スコアリングに使う攻撃技術IDの順序付きリスト。``None`` の場合は
            シナリオなしで探索する。
        max_nodes : int
            探索する経路の最大ノード数。

        Returns
        -------
        list of dict
            発見した攻撃経路のリスト。各要素は経路ノード列とリスクスコアを含む辞書。
        """
        ...


__all__ = ["PathSearcher", "ExhaustiveSearcher"]
