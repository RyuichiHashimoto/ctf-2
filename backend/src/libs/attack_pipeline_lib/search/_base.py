"""経路探索アルゴリズムの基底クラス。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from libs.attack_graph_lib.schema import GraphData


class PathSearcher(ABC):
    """経路探索アルゴリズムの基底クラス。

    新しいアルゴリズムを実装する場合は、このクラスを継承して
    ``search()`` を実装する。未実装のままインスタンス化しようとすると
    ``TypeError`` が発生する。
    """

    @abstractmethod
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
