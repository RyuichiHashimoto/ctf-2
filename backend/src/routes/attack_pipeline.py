from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from libs.attack_graph_lib.storage import load_uploaded_graph_payload
from libs.attack_pipeline_lib import PipelineInput, run_pipeline

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

PREDICTION_METHOD_EXHAUSTIVE_SPECIFIED = "exhaustive_specified"
PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED = "exhaustive_unspecified"
PREDICTION_METHOD_ALIASES = {
    "specified": PREDICTION_METHOD_EXHAUSTIVE_SPECIFIED,
    "start_end": PREDICTION_METHOD_EXHAUSTIVE_SPECIFIED,
    "unspecified": PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED,
    "all": PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED,
}


@router.post("/pipeline/predict")
def predict_from_pipeline(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Run the full attack prediction pipeline."""
    file_id = payload.get("network_configuration_file_id") or payload.get("netowork_configuration_file_id")
    method = payload.get("prediction_method", "exhaustive_unspecified")
    logger.info(
        "pipeline.predict start: file_id=%s method=%s start_nodes=%s target_nodes=%s",
        file_id,
        method,
        payload.get("start_nodes") or payload.get("start_node"),
        payload.get("target_nodes") or payload.get("end_nodes") or payload.get("end_node"),
    )
    try:
        input_data = _input_from_payload(payload)
        logger.info(
            "pipeline.predict input_ready: nodes=%d edges=%d vulns=%d start=%s target=%s",
            len(input_data.system.nodes),
            len(input_data.system.edges),
            len(input_data.vulnerabilities),
            input_data.start_nodes,
            input_data.target_nodes,
        )
        result = run_pipeline(input_data)
        logger.info(
            "pipeline.predict done: paths=%d elapsed=%.3fs",
            len(result.paths),
            result.metrics.get("elapsed_seconds", 0),
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        logger.warning("pipeline.predict file not found: file_id=%s", file_id)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as exc:
        logger.exception("pipeline.predict error")
        raise HTTPException(status_code=400, detail=str(exc))
    return result.asdict()


def _input_from_payload(payload: dict[str, Any]) -> PipelineInput:
    normalized_payload = _normalize_prediction_request(payload)
    file_id = payload.get("network_configuration_file_id") or payload.get("netowork_configuration_file_id")
    if not file_id:
        return PipelineInput.from_dict(normalized_payload)

    graph = load_uploaded_graph_payload(str(file_id))
    merged_payload = {**normalized_payload, "system": graph.asdict()}
    return PipelineInput.from_dict(merged_payload)


def _normalize_prediction_request(payload: dict[str, Any]) -> dict[str, Any]:
    method = _prediction_method(payload)
    if method == PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED:
        return payload

    start_node = payload.get("start_node")
    start_nodes_list = payload.get("start_nodes") or []
    resolved_start = str(start_node) if start_node else (str(start_nodes_list[0]) if start_nodes_list else None)

    end_nodes = _end_nodes(payload)
    if not resolved_start:
        raise HTTPException(
            status_code=400,
            detail="start_node is required when prediction_method is exhaustive_specified",
        )
    if not end_nodes:
        raise HTTPException(
            status_code=400,
            detail="end_node or end_nodes is required when prediction_method is exhaustive_specified",
        )

    return {
        **payload,
        "start_nodes": [resolved_start],
        "target_nodes": end_nodes,
    }


def _prediction_method(payload: dict[str, Any]) -> str:
    raw_method = str(payload.get("prediction_method") or PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED)
    method = PREDICTION_METHOD_ALIASES.get(raw_method, raw_method)
    if method not in {
        PREDICTION_METHOD_EXHAUSTIVE_SPECIFIED,
        PREDICTION_METHOD_EXHAUSTIVE_UNSPECIFIED,
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "prediction_method must be exhaustive_specified "
                "or exhaustive_unspecified"
            ),
        )
    return method


def _end_nodes(payload: dict[str, Any]) -> list[str]:
    if payload.get("end_node"):
        return [str(payload["end_node"])]
    if payload.get("target_node"):
        return [str(payload["target_node"])]

    raw_nodes = (
        payload.get("end_nodes")
        or payload.get("target_nodes")
        or []
    )
    return [str(item) for item in raw_nodes if item]
