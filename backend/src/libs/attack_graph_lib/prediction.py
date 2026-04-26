from __future__ import annotations

from typing import Any

import networkx as nx

from .schema import GraphData, GraphEdge, GraphNode, NodeType, asset_node_ids


def graph_to_data(graph: nx.DiGraph) -> GraphData:
    """Convert a NetworkX graph into a GraphData dataclass."""
    nodes = [
        GraphNode(
            id=str(node),
            label=str(graph.nodes[node].get("label", node)),
            type=NodeType.from_value(str(graph.nodes[node].get("type", "unknown"))),
            techniques=list(graph.nodes[node].get("techniques", [])),
            features=list(graph.nodes[node].get("features", [])),
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
    """Serialize a NetworkX graph into a JSON-friendly dict."""
    data = graph_to_data(graph)
    return {
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "type": node.type.value,
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


def build_graph_from_payload(payload: dict[str, Any]) -> nx.DiGraph:
    """Build a NetworkX graph from a JSON-like payload."""
    graph = nx.DiGraph()
    for node in payload.get("nodes", []):
        node_id = node.get("id")
        if node_id:
            graph.add_node(node_id, **node)
    for edge in payload.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            graph.add_edge(source, target, **edge)
    return graph


def build_graph_from_data(graph_data: GraphData) -> nx.DiGraph:
    """Build a NetworkX graph from a GraphData instance."""
    graph = nx.DiGraph()
    for node in graph_data.nodes:
        graph.add_node(
            node.id,
            id=node.id,
            label=node.label,
            type=node.type.value,
            techniques=list(node.techniques),
            features=list(node.features),
        )
    for edge in graph_data.edges:
        graph.add_edge(
            edge.source,
            edge.target,
            id=edge.id,
            source=edge.source,
            target=edge.target,
            risk=edge.risk,
        )
    return graph


def score_path(
    graph: nx.DiGraph,
    path: list[str],
    attack_scenario: list[str] | None = None,
) -> float:
    """Compute path risk score by multiplying edge probabilities."""
    score = 1.0
    for idx in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[idx], path[idx + 1], default={})
        score *= float(edge_data.get("risk", 1.0))

    if not attack_scenario:
        return score

    path_techniques_by_node = [
        set(graph.nodes.get(node_id, {}).get("techniques", []))
        for node_id in path
    ]
    if not any(path_techniques_by_node):
        return 0.0

    matched = 0
    cursor = 0
    for technique in attack_scenario:
        found = False
        for idx in range(cursor, len(path_techniques_by_node)):
            if technique in path_techniques_by_node[idx]:
                matched += 1
                cursor = idx
                found = True
                break
        if not found:
            break

    return score * (matched / len(attack_scenario))


def find_attack_path_candidates(
    graph: nx.Graph,
    start_node: str,
    target_nodes: set[str],
    max_nodes: int = 8,
    next_nodes: set[str] | None = None,
    via_nodes: set[str] | None = None,
) -> list[list[str]]:
    """Find simple attack path candidates using graph topology only."""
    if start_node not in graph:
        return []

    paths: list[list[str]] = []
    for target_node in target_nodes:
        if target_node not in graph:
            continue
        for path in nx.all_simple_paths(graph, start_node, target_node, cutoff=max_nodes):
            if next_nodes and (len(path) < 2 or path[1] not in next_nodes):
                continue
            if via_nodes and not via_nodes.intersection(path):
                continue
            paths.append(path)
    return paths


def predict_paths_with_risk(
    graph_payload_data: GraphData,
    start_node: str,
    attack_scenario: list[str] | None = None,
    max_nodes: int = 8,
    next_nodes: set[str] | None = None,
    via_nodes: set[str] | None = None,
    target_nodes: set[str] | None = None,
) -> dict[str, Any]:
    """Predict and score graph-local attack paths."""
    resolved_targets = target_nodes if target_nodes else set(asset_node_ids(graph_payload_data))
    graph_networkx = build_graph_from_data(graph_payload_data)
    attack_paths = find_attack_path_candidates(
        graph_networkx,
        start_node,
        resolved_targets,
        max_nodes=max_nodes,
        next_nodes=next_nodes,
        via_nodes=via_nodes,
    )
    attack_path_with_risk = [
        {"nodes": path, "risk": score_path(graph_networkx, path, attack_scenario)}
        for path in attack_paths
    ]
    attack_path_with_risk.sort(key=lambda item: item["risk"], reverse=True)
    return {"paths": attack_path_with_risk}
