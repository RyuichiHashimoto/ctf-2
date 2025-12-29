"""Attack graph API routes (FastAPI layer)."""

from __future__ import annotations

import logging
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Any, dict

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile

from .api import graph_payload, predict_paths, predict_paths_from_payload
from .schema import load_graph_from_json_path, parse_graph_payload, validate_graph
from .storage import (
    load_graph,
    load_uploaded_graph_payload,
    record_upload,
    save_graph,
    list_uploads,
    clear_uploads,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.get("/graph")
def get_graph(request: Request) -> dict[str, Any]:
    """永続化されたグラフを取得して返す。"""
    graph = load_graph()
    response = graph_payload(graph)
    logger.info("GET /graph response=%s", response)
    return response


@router.post("/graph/upload")
async def upload_graph(file: UploadFile = File(...)) -> dict[str, Any]:
    """JSONファイルをアップロードして保存し、正規化済みグラフを返す。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
        
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_id = uuid.uuid4().hex
        json_file = "network_content.json"
        db_file = "network_content.db"

        tmp_json_path = Path(tmp_dir) / f"{file_id}"/ json_file
        tmp_db_path = Path(tmp_dir) / f"{file_id}" / db_file
        
        target_json_path = UPLOAD_DIR / f"{file_id}"/ json_file
        target_db_path = UPLOAD_DIR / f"{file_id}" / db_file

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
                    
        
        print(tmp_db_path)
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
    logger.debug("POST /graph/upload response=%s", response)
    return response


@router.get("/graph/upload/{file_id}")
def get_uploaded_graph(file_id: str) -> dict[str, Any]:
    """保存済みグラフJSONを読み込み、正規化した結果を返す。"""
    try:
        payload = load_uploaded_graph_payload(file_id)
        if not payload:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception:
        logger.error("graph.uploads read error file_id=%s", file_id)
        raise HTTPException(status_code=400, detail="Invalid stored JSON")
    try:
        validate_graph(parse_graph_payload(payload.graph))
    except ValueError as exc:
        logger.error("graph.uploads validate error file_id=%s detail=%s", file_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    response = {"file_id": payload.file_id, "graph": payload.graph}
    logger.debug("GET /graph/uploads/%s response=%s", file_id, response)
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


@router.get("/predict")
def get_predicted_paths(
    request: Request,
    start: str = Query(..., description="Starting node id"),
    target: str | None = Query(None, description="Target node id"),
    max_len: int = Query(6, ge=2, le=10)
) -> dict[str, Any]:
    """保存済みグラフに対して経路予測を実行して返す。"""
    client = request.client.host if request.client else "unknown"
    logger.info(
        "GET /predict from %s start=%s target=%s max_len=%s",
        client,
        start,
        target,
        max_len
    )
    graph = load_graph()
    response = predict_paths(graph, start=start, target=target, max_len=max_len)
    logger.info("GET /predict response=%s", response)
    return response


@router.post("/predict/paths")
def predict_paths_from_request(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """ペイロードで渡されたグラフに対して経路予測を行う。"""
    start = payload.get("start")
    technique_filter = payload.get("technique")
    feature_filter = payload.get("feature")
    max_len = int(payload.get("max_len", 8))
    graph_payload_data = payload.get("graph") or {}
    if not start:
        logger.info("POST /predict/paths payload=%s response=empty_start", payload)
        return {"paths": []}
    response = predict_paths_from_payload(
        graph_payload_data=graph_payload_data,
        start=start,
        technique_filter=technique_filter,
        feature_filter=feature_filter,
        max_len=max_len
    )
    if not response.get("paths"):
        logger.info("POST /predict/paths payload=%s response=start_not_found", payload)
    else:
        logger.info("POST /predict/paths payload=%s response_paths=%s", payload, len(response["paths"]))
    return response
