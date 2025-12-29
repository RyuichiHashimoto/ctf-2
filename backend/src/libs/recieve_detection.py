from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect
import logging

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

active_detection_sockets: set[WebSocket] = set()


@router.post("/detection")
async def receive_detection(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    logger.info("POST /detection payload=%s", payload)
    message = {
        "device_id": payload.get("device_id"),
        "event": payload.get("event"),
        "detail": payload.get("detail"),
    }
    for ws in list(active_detection_sockets):
        try:
            await ws.send_json(message)
        except Exception:
            active_detection_sockets.discard(ws)
    return {
        "status": "ok",
        **message,
    }


@router.websocket("/ws/detection")
async def detection_socket(ws: WebSocket) -> None:
    await ws.accept()
    active_detection_sockets.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        active_detection_sockets.discard(ws)
