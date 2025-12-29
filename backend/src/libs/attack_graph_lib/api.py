from __future__ import annotations

from typing import Any, Dict, List, Optional

import networkx as nx

from .schema import GraphData, GraphEdge, GraphNode


def graph_to_data(graph: nx.DiGraph) -> GraphData:
    nodes = [
        GraphNode(
            id=str(node),
            label=str(graph.nodes[node].get("label", node)),
            type=str(graph.nodes[node].get("type", "unknown")),
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
            prob=float(data.get("prob", 0.1)),
            technique=str(data.get("technique", ""))
        )
        for source, target, data in graph.edges(data=True)
    ]
    return GraphData(nodes=nodes, edges=edges)


def graph_payload(graph: nx.DiGraph) -> Dict[str, Any]:
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
                "prob": edge.prob,
                "technique": edge.technique,
            }
            for edge in data.edges
        ],
    }


def score_path(graph: nx.DiGraph, path: List[str]) -> float:
    score = 1.0
    for idx in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[idx], path[idx + 1], default={})
        score *= float(edge_data.get("prob", 0.1))
    return score


def build_graph_from_payload(payload: Dict[str, Any]) -> nx.DiGraph:
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


def compute_next_steps(graph: nx.DiGraph, start: str) -> List[Dict[str, Any]]:
    next_steps = [
        {
            "source": start,
            "target": neighbor,
            "prob": float(graph.get_edge_data(start, neighbor).get("prob", 0.1))
        }
        for neighbor in graph.successors(start)
    ]
    next_steps.sort(key=lambda item: item["prob"], reverse=True)
    return next_steps


def predict_paths(
    graph: nx.DiGraph,
    start: str,
    target: Optional[str] = None,
    max_len: int = 6
) -> Dict[str, Any]:
    if start not in graph.nodes:
        return {"paths": [], "next_steps": []}
    next_steps = compute_next_steps(graph, start)

    if target and target in graph.nodes:
        paths = []
        for path in nx.all_simple_paths(graph, start, target, cutoff=max_len):
            score = score_path(graph, path)
            paths.append({"nodes": path, "score": score})
        paths.sort(key=lambda item: item["score"], reverse=True)
        return {"paths": paths[:5], "next_steps": next_steps}

    goal_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "goal"]
    suggestions = []
    for goal in goal_nodes:
        for path in nx.all_simple_paths(graph, start, goal, cutoff=max_len):
            suggestions.append({"target": goal, "nodes": path, "score": score_path(graph, path)})
    suggestions.sort(key=lambda item: item["score"], reverse=True)
    return {"paths": suggestions[:5], "next_steps": next_steps}


def predict_paths_from_payload(
    graph_payload_data: Dict[str, Any],
    start: str,
    technique_filter: Optional[str],
    feature_filter: Optional[str],
    max_len: int = 8
) -> Dict[str, Any]:
    graph = build_graph_from_payload(graph_payload_data)
    if start not in graph.nodes:
        return {"paths": []}
    targets = [
        node_id
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "asset"
    ]
    paths = []
    for target in targets:
        for path in nx.all_simple_paths(graph, start, target, cutoff=max_len):
            risk_override = None
            if technique_filter:
                if len(path) < 2:
                    risk_override = 0.0
                else:
                    next_node = graph.nodes.get(path[1], {})
                    allowed = next_node.get("techniques") or []
                    if technique_filter not in allowed:
                        risk_override = 0.0
            if feature_filter:
                has_feature = False
                for node_id in path:
                    node_data = graph.nodes.get(node_id, {})
                    features = node_data.get("features") or []
                    if feature_filter in features:
                        has_feature = True
                        break
                if not has_feature:
                    continue
            paths.append(
                {
                    "nodes": path,
                    "risk": risk_override if risk_override is not None else score_path(graph, path),
                    "target": target,
                }
            )
    paths.sort(key=lambda item: item["risk"], reverse=True)
    return {"paths": paths}
