"""Attack graph API routes (FastAPI layer)."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

from libs.attack_graph_lib.api import predict_paths_with_risk
from libs.attack_graph_lib.filter import derive_path_filters_from_obtained_data
from libs.attack_graph_lib.schema import load_graph_from_json_path, validate_graph
from libs.attack_graph_lib.storage import (
    UPLOAD_DIR,
    clear_uploads,
    list_uploads,
    load_uploaded_graph_payload,
    record_upload,
    save_graph,
)
from libs.attack_scenario import fetch_scenario_steps

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.post("/graph/upload")
async def upload_graph(file: UploadFile = File(...)) -> dict[str, Any]:
    """JSONファイルをアップロードして保存し、正規化済みグラフを返す。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    with tempfile.TemporaryDirectory() as tmp_dir:
        file_id = uuid.uuid4().hex
        json_file = "network_content.json"
        db_file = "network_content.db"

        tmp_json_path = Path(tmp_dir) / file_id / json_file
        tmp_db_path = Path(tmp_dir) / file_id / db_file

        target_json_path = UPLOAD_DIR / file_id / json_file
        target_db_path = UPLOAD_DIR / file_id / db_file

        tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
        target_db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            content = await file.read()
            tmp_json_path.write_bytes(content)
        except Exception:
            logger.exception("graph.upload load file error filename=%s", file.filename)
            raise HTTPException(status_code=400, detail={"code": "failure", "message": "load file error"})

        try:
            graph = load_graph_from_json_path(tmp_json_path)
            validate_graph(graph)
        except Exception:
            logger.exception("graph.upload parse error filename=%s", file.filename)
            raise HTTPException(status_code=400, detail={"code": "failure", "message": "parse error"})

        save_graph(graph, tmp_db_path)

        shutil.move(str(tmp_json_path), str(target_json_path))
        shutil.move(str(tmp_db_path), str(target_db_path))

    record_upload(
        file_uuid=file_id,
        filename=file.filename,
        stored_json_name=target_json_path.name,
        stored_sqlite_name=target_db_path.name,
    )
    response = {
        "status": "success",
        "file_id": file_id,
        "message": "Upload successful",
    }
    logger.info("POST /graph/upload response=%s", response)
    return response


@router.get("/graph/upload/{file_id}")
def get_uploaded_graph(file_id: str) -> dict[str, Any]:
    """保存済みグラフJSONを読み込み、正規化した結果を返す。"""
    try:
        payload = load_uploaded_graph_payload(file_id)
    except HTTPException:
        raise
    except Exception:
        logger.error("graph.uploads read error file_id=%s", file_id)
        raise HTTPException(status_code=400, detail="Invalid stored JSON")

    try:
        validate_graph(payload)
    except ValueError as exc:
        logger.error("graph.upload validate error file_id=%s detail=%s", file_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))

    response = {"graph": payload.asdict()}
    logger.info("GET /graph/upload/%s response=%s", file_id, response)
    return response


@router.get("/graph/uploads")
def list_uploaded_graphs() -> dict[str, Any]:
    """アップロード済みグラフJSONの一覧を返す。"""
    response = {"files": list_uploads()}
    logger.info("GET /graph/uploads response=%s", response)
    return response


@router.delete("/graph/uploads/clear")
def clear_uploaded_graphs() -> dict[str, Any]:
    """アップロード済みファイルを削除する。"""
    removed = clear_uploads()
    response = {"status": "success", "removed": removed}
    logger.info("DELETE /graph/uploads/clear response=%s", response)
    return response


@router.post("/predict/paths")
def predict_paths_from_request(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """ペイロードで渡されたグラフに対して経路予測を行う。"""
    network_configuration_file_id = (
        payload.get("network_configuration_file_id")
        or payload.get("netowork_configuration_file_id")
    )
    start = payload.get("start_node")
    max_len = 8
    next_nodes = payload.get("next_nodes")
    via_nodes = payload.get("via_nodes")
    target_nodes = payload.get("target_nodes")
    scenario_id = payload.get("scenario_id")
    attacker_obtained_data = payload.get("attacker_obtained_data") or payload.get("attack_data")

    if not start:
        logger.error("POST /predict/paths payload=%s response=empty_start", payload)
        return {"paths": []}
    if not network_configuration_file_id:
        logger.error("POST /predict/paths payload=%s response=empty_file_id", payload)
        return {"paths": []}

    next_nodes = set(next_nodes) if next_nodes else set()
    via_nodes = set(via_nodes) if via_nodes else set()
    target_nodes = set(target_nodes) if target_nodes else set()

    try:
        uploaded_graph = load_uploaded_graph_payload(network_configuration_file_id)
    except FileNotFoundError:
        logger.error("predict.paths load error file_id=%s", network_configuration_file_id)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception:
        logger.error("predict.paths load error file_id=%s", network_configuration_file_id)
        raise HTTPException(status_code=400, detail="Invalid stored JSON")

    attack_scenario = None
    if scenario_id is not None:
        try:
            scenario_id_int = int(scenario_id)
        except (TypeError, ValueError):
            logger.error("predict.paths invalid scenario_id=%s", scenario_id)
            scenario_id_int = None
        if scenario_id_int is not None:
            attack_scenario = fetch_scenario_steps(scenario_id_int)

    if attacker_obtained_data is not None:
        derived_next_nodes, derived_via_nodes, derived_target_nodes = derive_path_filters_from_obtained_data(
            uploaded_graph,
            attacker_obtained_data,
        )
        next_nodes = next_nodes.union(derived_next_nodes)
        via_nodes = via_nodes.union(derived_via_nodes)
        target_nodes = target_nodes.union(derived_target_nodes)

    response = predict_paths_with_risk(
        graph_payload_data=uploaded_graph,
        start_node=start,
        attack_scenario=attack_scenario,
        max_nodes=max_len,
        next_nodes=next_nodes,
        via_nodes=via_nodes,
        target_nodes=target_nodes,
    )
    if not response.get("paths"):
        logger.info("POST /predict/paths payload=%s response=start_not_found", payload)
    else:
        logger.info("POST /predict/paths payload=%s response_paths=%s", payload, len(response["paths"]))
    return response
