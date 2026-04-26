from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from libs.attack_graph_lib.storage import load_uploaded_graph_payload
from libs.attack_pipeline_lib.pipeline import run_pipeline
from libs.attack_pipeline_lib.schema import PipelineInput

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
    try:
        input_data = _input_from_payload(payload)
        result = run_pipeline(input_data)
    except HTTPException:
        raise
    except FileNotFoundError:
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
    end_nodes = _end_nodes(payload)
    if not start_node:
        raise HTTPException(
            status_code=400,
            detail="start_node is required when prediction_method is exhaustive_specified",
        )
    if not end_nodes:
        raise HTTPException(
            status_code=400,
            detail="end_node or end_nodes is required when prediction_method is exhaustive_specified",
        )

    api_threat = {
        "id": "__api_prediction_bounds__",
        "start_node": str(start_node),
        "target_nodes": end_nodes,
    }
    return {
        **payload,
        "threats": [*payload.get("threats", []), api_threat],
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
