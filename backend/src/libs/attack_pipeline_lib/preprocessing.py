"""攻撃経路予測パイプラインの前処理。

脆弱性情報と脅威情報に含まれる攻撃技術をグラフノードへ付与し、
後続の経路探索・スコアリングで利用しやすい形へ正規化する。
"""

from __future__ import annotations

from dataclasses import replace

from libs.attack_graph_lib.preprocessing import normalize_graph
from libs.attack_graph_lib.schema import GraphData, GraphNode

from .schema import Threat, Vulnerability


def integrate_context(
    graph: GraphData,
    vulnerabilities: list[Vulnerability],
    threats: list[Threat],
) -> tuple[GraphData, list[str]]:
    """脆弱性・脅威情報をグラフへ統合する。

    Args:
        graph: 前処理対象のシステム構成グラフ。
        vulnerabilities: ノードに紐付く脆弱性情報の一覧。`node_id` がグラフ上の
            ノードIDと一致する場合、その脆弱性の `techniques` を対象ノードへ
            追加する。
        threats: 脅威情報の一覧。`start_node` がグラフ上のノードIDと一致する
            場合、その脅威の `techniques` を開始ノードへ追加する。

    Returns:
        脆弱性・脅威由来の攻撃技術を付与した正規化済みグラフと、脅威情報から
        導出した攻撃シナリオの technique リスト。
    """
    techniques_by_node: dict[str, set[str]] = {node.id: set(node.techniques) for node in graph.nodes}

    for vulnerability in vulnerabilities:
        if vulnerability.node_id and vulnerability.node_id in techniques_by_node:
            techniques_by_node[vulnerability.node_id].update(vulnerability.techniques)

    for threat in threats:
        if threat.start_node and threat.start_node in techniques_by_node:
            techniques_by_node[threat.start_node].update(threat.techniques)

    nodes: list[GraphNode] = [
        replace(node, techniques=sorted(techniques_by_node[node.id]))
        for node in graph.nodes
    ]
    attack_scenario = _derive_attack_scenario(threats)
    return normalize_graph(GraphData(nodes=nodes, edges=list(graph.edges), contains=list(graph.contains))), attack_scenario


def _derive_attack_scenario(threats: list[Threat]) -> list[str]:
    """脅威情報から攻撃シナリオを導出する。

    Args:
        threats: 攻撃技術を含む脅威情報の一覧。

    Returns:
        `threats` に出現した順序を保った、重複なしの technique リスト。
    """
    scenario: list[str] = []
    seen: set[str] = set()
    for threat in threats:
        for technique in threat.techniques:
            if technique in seen:
                continue
            seen.add(technique)
            scenario.append(technique)
    return scenario
