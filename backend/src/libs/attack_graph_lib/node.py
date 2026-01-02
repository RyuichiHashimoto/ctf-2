from __future__ import annotations

from typing import Any

import networkx as nx

from .schema import GraphData, GraphEdge, GraphNode, NodeType, asset_node_ids


def graph_to_data(graph: nx.DiGraph) -> GraphData:
    """Convert a NetworkX graph into a GraphData dataclass.

    Args:
        graph: NetworkX directed graph to serialize.

    Returns:
        GraphData representation of the graph.
    """
    nodes = [
        GraphNode(
            id=str(node),
            label=str(graph.nodes[node].get("label", node)),
            type=NodeType.from_value(str(graph.nodes[node].get("type", "unknown"))),
            techniques=list(graph.nodes[node].get("techniques", [])),
            features=list(graph.nodes[node].get("features", []))
        )
        for node in graph.nodes
    ]
    edges = [
        GraphEdge(
            id=str(data.get("id", f"{source}->{target}")),
            source=str(source),
            target=str(target),
            risk=float(data.get("risk", 0.1)),
        )
        for source, target, data in graph.edges(data=True)
    ]
    return GraphData(nodes=nodes, edges=edges)


def graph_payload(graph: nx.DiGraph) -> dict[str, Any]:
    """Serialize a NetworkX graph into a JSON-friendly dict.

    Args:
        graph: NetworkX directed graph to serialize.

    Returns:
        JSON-friendly dict with nodes and edges.
    """
    data = graph_to_data(graph)
    return {
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "techniques": node.techniques,
                "features": node.features,
            }
            for node in data.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "risk": edge.risk,
            }
            for edge in data.edges
        ],
    }


def score_path(graph: nx.DiGraph, path: list[str], attack_scenario: list[str] | None) -> float:
    """Compute path risk score by multiplying edge probabilities.

    Args:
        graph: NetworkX directed graph.
        path: Ordered list of node ids.

    Returns:
        Multiplicative risk score for the path.
    """
    score = 1.0
    for idx in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[idx], path[idx + 1], default={})
        score *= float(edge_data.get("risk", 1.0))
    
    if not attack_scenario:
        return score

    # 経路上の各ノードに紐づくテクニックを集合として収集する
    path_techniques_by_node: list[set[str]] = []
    for node_id in path:
        node_data = graph.nodes.get(node_id, {})
        path_techniques_by_node.append(set(node_data.get("techniques", [])))

    # 経路上にテクニックが存在しない場合は一致率が定義できないため 0 を返す
    if not any(path_techniques_by_node):
        return 0.0

    # attack_scenario の順序だけを維持し、ノード内は順不同として一致を確認する
    matched = 0
    cursor = 0
    for technique in attack_scenario:
        found = False
        for idx in range(cursor, len(path_techniques_by_node)):
            if technique in path_techniques_by_node[idx]:
                matched += 1
                # 同一ノード内で複数テクニックが一致する可能性があるため、同じノードを許可する
                cursor = idx
                found = True
                break
        if not found:
            break

    # 一致率をリスクスコアに反映する
    match_rate = matched / len(attack_scenario)
    return score * match_rate


def build_graph_from_payload(payload: dict[str, Any]) -> nx.DiGraph:
    """Build a NetworkX graph from a JSON-like payload.

    Args:
        payload: Dict containing nodes and edges.

    Returns:
        NetworkX directed graph built from the payload.
    """
    graph = nx.DiGraph()
    for node in payload.get("nodes", []):
        node_id = node.get("id")
        if not node_id:
            continue
        graph.add_node(node_id, **node)
    for edge in payload.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        graph.add_edge(source, target, **edge)
    return graph


def build_graph_from_data(graph_data: GraphData) -> nx.DiGraph:
    """Build a NetworkX graph from a GraphData instance.

    Args:
        graph_data: GraphData to convert.

    Returns:
        NetworkX directed graph built from GraphData.
    """
    graph = nx.DiGraph()
    for node in graph_data.nodes:
        graph.add_node(
            node.id,
            id=node.id,
            label=node.label,
            type=node.type.value,
            techniques=list(node.techniques),
            features=list(node.features)
        )
    for edge in graph_data.edges:
        graph.add_edge(
            edge.source,
            edge.target,
            id=edge.id,
            source=edge.source,
            target=edge.target,
            risk=edge.risk
        )
    return graph
