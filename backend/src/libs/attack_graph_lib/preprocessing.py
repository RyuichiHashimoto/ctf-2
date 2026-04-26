from __future__ import annotations

from .schema import GraphData, GraphEdge, GraphNode, validate_graph


def normalize_graph(graph: GraphData) -> GraphData:
    """Return a validated graph with stable node and edge values."""
    nodes = [
        GraphNode(
            id=node.id.strip(),
            label=(node.label or node.id).strip(),
            type=node.type,
            techniques=list(dict.fromkeys(node.techniques)),
            features=list(dict.fromkeys(node.features)),
        )
        for node in graph.nodes
    ]
    edges = [
        GraphEdge(
            id=edge.id.strip() if edge.id else f"{edge.source}->{edge.target}",
            source=edge.source.strip(),
            target=edge.target.strip(),
            risk=edge.risk,
        )
        for edge in graph.edges
    ]
    normalized = GraphData(nodes=nodes, edges=edges, contains=list(graph.contains))
    validate_graph(normalized)
    return normalized
