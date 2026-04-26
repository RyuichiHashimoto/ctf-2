from __future__ import annotations

from typing import Any


def deduplicate_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate node sequences while preserving highest-ranked order."""
    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, Any]] = []
    for path in paths:
        key = tuple(str(node_id) for node_id in path.get("nodes", []))
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def limit_paths(paths: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    """Apply an optional top-k limit to path results."""
    if limit is None or limit < 1:
        return paths
    return paths[:limit]


def postprocess_prediction(
    prediction: dict[str, Any],
    limit: int | None = None,
) -> dict[str, Any]:
    """Postprocess a graph-local prediction response."""
    paths = deduplicate_paths(list(prediction.get("paths") or []))
    paths = limit_paths(paths, limit)
    return {"paths": paths}
