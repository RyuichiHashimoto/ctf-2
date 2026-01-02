from __future__ import annotations

from collections.abc import Iterable

from .schema import GraphData, NodeType


def derive_path_filters_from_obtained_data(
    graph: GraphData,
    attacker_obtained_data: str | Iterable[str] | None,
) -> tuple[set[str], set[str], set[str]]:
    """Return via_nodes and target_nodes derived from attacker obtained data."""
    if not attacker_obtained_data:
        return set(), set(), set()

    if isinstance(attacker_obtained_data, str):
        data_items = [attacker_obtained_data]
    else:
        data_items = [item for item in attacker_obtained_data if item]

    data_set = {item.strip() for item in data_items if item and str(item).strip()}
    if not data_set:
        return set(), set(), set()

    next_nodes: set[str] = set()
    via_nodes: set[str] = set()
    target_nodes: set[str] = set()

    for node in graph.nodes:
        if not node.features:
            continue
        if not data_set.intersection(node.features):
            continue
        if node.type == NodeType.ASSET:
            target_nodes.add(node.id)
        else:
            via_nodes.add(node.id)

    return next_nodes, via_nodes, target_nodes
