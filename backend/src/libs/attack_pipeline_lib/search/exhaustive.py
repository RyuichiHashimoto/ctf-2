"""全経路探索アルゴリズム。"""

from __future__ import annotations

from typing import Any

from libs.attack_graph_lib.prediction import predict_paths_with_risk
from libs.attack_graph_lib.schema import GraphData


class ExhaustiveSearcher:
    """既存の全経路探索を PathSearcher インターフェースでラップした実装。

    ``attack_graph_lib.prediction.predict_paths_with_risk`` を呼び出し、
    ``PathSearcher`` プロトコルに準拠したインターフェースを提供する。
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
        prediction = predict_paths_with_risk(
            graph_payload_data=graph,
            start_node=start_node,
            attack_scenario=attack_scenario,
            max_nodes=max_nodes,
            target_nodes=target_nodes,
        )
        return prediction.get("paths", [])
