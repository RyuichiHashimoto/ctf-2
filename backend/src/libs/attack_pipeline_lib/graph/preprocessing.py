"""攻撃経路予測パイプラインの前処理。

脆弱性情報に含まれる攻撃技術をグラフノードへ付与し、
後続の経路探索・スコアリングで利用しやすい形へ正規化する。
"""

from __future__ import annotations

from dataclasses import replace

from libs.attack_graph_lib.preprocessing import normalize_graph
from libs.attack_graph_lib.schema import GraphData, GraphNode

from ..models.schema import Vulnerability


def integrate_context(
    graph: GraphData,
    vulnerabilities: list[Vulnerability],
) -> GraphData:
    """脆弱性情報をグラフへ統合する。

    Parameters
    ----------
    graph : GraphData
        前処理対象のシステム構成グラフ。
    vulnerabilities : list of Vulnerability
        ノードに紐付く脆弱性情報の一覧。``node_id`` がグラフ上のノードIDと
        一致する場合、その脆弱性の ``techniques`` を対象ノードへ追加する。

    Returns
    -------
    GraphData
        脆弱性由来の攻撃技術を付与した正規化済みグラフ。
    """
    techniques_by_node: dict[str, set[str]] = {node.id: set(node.techniques) for node in graph.nodes}

    for vulnerability in vulnerabilities:
        if vulnerability.node_id and vulnerability.node_id in techniques_by_node:
            techniques_by_node[vulnerability.node_id].update(vulnerability.techniques)

    nodes: list[GraphNode] = [
        replace(node, techniques=sorted(techniques_by_node[node.id]))
        for node in graph.nodes
    ]
    return normalize_graph(GraphData(nodes=nodes, edges=list(graph.edges), contains=list(graph.contains)))
