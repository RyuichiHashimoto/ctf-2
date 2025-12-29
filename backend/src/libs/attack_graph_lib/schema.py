from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


class AsDictMixin:
    def asdict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class GraphNode(AsDictMixin):
    id: str
    label: str
    type: str
    techniques: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)

    
@dataclass(frozen=True)
class GraphEdge(AsDictMixin):
    id: str
    source: str
    target: str
    risk: float = 0.1

@dataclass(frozen=True)
class GraphContain(AsDictMixin):
    id: str
    parent: str
    child: str
    label: str = ""


@dataclass(frozen=True)
class GraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    contains: list[GraphContain] = field(default_factory=list)


def _parse_node(raw: dict[str, Any]) -> GraphNode:
    node_id = raw.get("id")
    if not node_id:
        raise ValueError("node.id is required")
    return GraphNode(
        id=str(node_id),
        label=str(raw.get("label") or raw.get("labe;") or node_id),
        type=str(raw.get("type") or "unknown"),
        techniques=list(raw.get("techniques") or []),
        features=list(raw.get("features") or [])
    )


def _parse_edge(raw: dict[str, Any], index: int) -> GraphEdge:
    source = raw.get("source")
    target = raw.get("target")
    if not source or not target:
        raise ValueError("edge.source and edge.target are required")
    edge_id = raw.get("id") or f"edge-{index}"
    return GraphEdge(
        id=str(edge_id),
        source=str(source),
        target=str(target),
        risk=float(raw.get("risk", 0.1)),
    )


def _parse_contain(raw: dict[str, Any], index: int) -> GraphContain:
    source = raw.get("parent")
    target = raw.get("child")
    if not source or not target:
        raise ValueError("contain.parent and contain.child are required")
    return GraphContain(
        parent=str(source),
        child=str(target),
        id=str(raw.get("id")) if raw.get("id") else f"contain-{index}",
        label=str(raw.get("label") or "")
    )


def load_graph_from_json_path(path: Path | str) -> GraphData:
    """JSONファイルからGraphDataを読み込む。"""
    json_path = Path(path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return parse_graph_payload(payload)


def parse_graph_payload(payload: dict[str, Any]) -> GraphData:
    """payloadをGraphDataへ変換する。"""
    graph = payload.get("graph") or payload
    nodes_raw = graph.get("node") or graph.get("nodes") or []
    edges_raw = graph.get("edge") or graph.get("edges") or []
    contains_raw = graph.get("contains") or []

    nodes = [_parse_node(node) for node in nodes_raw]
    edges = [_parse_edge(edge, index) for index, edge in enumerate(edges_raw)]
    contains = [_parse_contain(item, index) for index, item in enumerate(contains_raw)]
    return GraphData(nodes=nodes, edges=edges, contains=contains)


def _find_duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)


def validate_graph(graph: GraphData) -> None:
    """Graphの整合性を検証し、問題があれば例外を投げる。"""
    errors: list[str] = []

    node_ids = [node.id for node in graph.nodes]
    edge_ids = [edge.id for edge in graph.edges]
    contain_ids = [contain.id for contain in graph.contains if contain.id]

    node_dups = _find_duplicates(node_ids)
    if node_dups:
        errors.append(f"node.id duplicate: {', '.join(node_dups)}")

    edge_dups = _find_duplicates(edge_ids)
    if edge_dups:
        errors.append(f"edge.id duplicate: {', '.join(edge_dups)}")

    contain_dups = _find_duplicates(contain_ids)
    if contain_dups:
        errors.append(f"contain.id duplicate: {', '.join(contain_dups)}")

    node_id_set = set(node_ids)
    missing_edge_nodes = sorted(
        {edge.source for edge in graph.edges if edge.source not in node_id_set}
        | {edge.target for edge in graph.edges if edge.target not in node_id_set}
    )
    if missing_edge_nodes:
        errors.append(f"edge references missing nodes: {', '.join(missing_edge_nodes)}")

    missing_contain_nodes = sorted(
        {contain.source for contain in graph.contains if contain.source not in node_id_set}
        | {contain.target for contain in graph.contains if contain.target not in node_id_set}
    )
    if missing_contain_nodes:
        errors.append(f"contain references missing nodes: {', '.join(missing_contain_nodes)}")

    if errors:
        raise ValueError("; ".join(errors))

if __name__ == "__main__":
    data = "../../../data/sample_configuration_1.json"
    a = load_graph_from_json_path(data)
    print(a)
