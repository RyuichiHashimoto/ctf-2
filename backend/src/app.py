from __future__ import annotations

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from libs.attack_graph_lib import api_router as graph_router, init_db
from libs.mitre import router as mitre_router
from libs.recieve_detection import router as receive_detection_router

app = FastAPI(title="Attack Path Visualizer API")
logger = logging.getLogger("uvicorn.error")

LOG_FORMAT = "[%(levelname)s] %(asctime)s : %(message)s"

def configure_logging() -> None:
    formatter = logging.Formatter(LOG_FORMAT)
    for name in ("uvicorn.error", "uvicorn.access"):
        target = logging.getLogger(name)
        for handler in target.handlers:
            handler.setFormatter(formatter)

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "*")
origin_list = [origin.strip() for origin in frontend_origin.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origin_list if frontend_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def on_startup() -> None:
    configure_logging()
    init_db()



app.include_router(graph_router)
app.include_router(mitre_router)
app.include_router(receive_detection_router)
