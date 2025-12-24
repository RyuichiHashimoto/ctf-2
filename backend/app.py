from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import os
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import Body, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
import logging
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "attack_graph.db"
MITRE_DB_PATH = Path(os.environ.get("MITRE_DB_PATH", DATA_DIR / "mitre_attack.db"))

app = FastAPI(title="Attack Path Visualizer API")
logger = logging.getLogger("uvicorn.error")

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_mitre_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(MITRE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            data_json TEXT NOT NULL,
            FOREIGN KEY(source) REFERENCES nodes(id),
            FOREIGN KEY(target) REFERENCES nodes(id)
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) as count FROM nodes")
    if cur.fetchone()["count"] == 0:
        seed_sample(conn)
    conn.close()


def seed_sample(conn: sqlite3.Connection) -> None:
    nodes = [
        {"id": "entry", "label": "Initial Access", "type": "entry"},
        {"id": "phish", "label": "Phishing", "type": "tactic"},
        {"id": "cred", "label": "Credential Dump", "type": "tactic"},
        {"id": "vpn", "label": "VPN Pivot", "type": "pivot"},
        {"id": "srv", "label": "App Server", "type": "asset"},
        {"id": "db", "label": "Database", "type": "asset"},
        {"id": "domain", "label": "Domain Admin", "type": "goal"},
        {"id": "exfil", "label": "Data Exfiltration", "type": "goal"}
    ]
    edges = [
        {
            "id": "e1",
            "source": "entry",
            "target": "phish",
            "prob": 0.7,
            "technique": "T1566"
        },
        {
            "id": "e2",
            "source": "phish",
            "target": "cred",
            "prob": 0.6,
            "technique": "T1003"
        },
        {
            "id": "e3",
            "source": "cred",
            "target": "vpn",
            "prob": 0.5,
            "technique": "T1078"
        },
        {
            "id": "e4",
            "source": "vpn",
            "target": "srv",
            "prob": 0.55,
            "technique": "T1090"
        },
        {
            "id": "e5",
            "source": "srv",
            "target": "db",
            "prob": 0.4,
            "technique": "T1505"
        },
        {
            "id": "e6",
            "source": "db",
            "target": "exfil",
            "prob": 0.45,
            "technique": "T1041"
        },
        {
            "id": "e7",
            "source": "cred",
            "target": "domain",
            "prob": 0.3,
            "technique": "T1068"
        },
        {
            "id": "e8",
            "source": "srv",
            "target": "domain",
            "prob": 0.2,
            "technique": "T1075"
        }
    ]
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO nodes (id, data_json) VALUES (?, ?)",
        [(node["id"], json.dumps(node)) for node in nodes]
    )
    cur.executemany(
        "INSERT INTO edges (id, source, target, data_json) VALUES (?, ?, ?, ?)",
        [(edge["id"], edge["source"], edge["target"], json.dumps(edge)) for edge in edges]
    )
    conn.commit()


def load_graph() -> nx.DiGraph:
    conn = get_conn()
    cur = conn.cursor()
    graph = nx.DiGraph()

    for row in cur.execute("SELECT id, data_json FROM nodes"):
        data = json.loads(row["data_json"])
        node_id = data["id"]
        graph.add_node(node_id, **data)

    for row in cur.execute("SELECT id, source, target, data_json FROM edges"):
        data = json.loads(row["data_json"])
        graph.add_edge(row["source"], row["target"], **data)

    conn.close()
    return graph


def graph_payload(graph: nx.DiGraph) -> Dict[str, Any]:
    nodes = [
        {
            "id": node,
            "label": graph.nodes[node].get("label", node),
            "type": graph.nodes[node].get("type", "unknown")
        }
        for node in graph.nodes
    ]
    edges = [
        {
            "id": data.get("id", f"{source}->{target}"),
            "source": source,
            "target": target,
            "prob": data.get("prob", 0.1),
            "technique": data.get("technique", "")
        }
        for source, target, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


def score_path(graph: nx.DiGraph, path: List[str]) -> float:
    score = 1.0
    for idx in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[idx], path[idx + 1], default={})
        score *= float(edge_data.get("prob", 0.1))
    return score


def build_graph_from_payload(payload: Dict[str, Any]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in payload.get("nodes", []):
        node_id = node.get("id")
        if not node_id:
            continue
        graph.add_node(node_id, **node)
    for edge in payload.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        graph.add_edge(source, target, **edge)
    return graph


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/graph")
def get_graph(request: Request) -> Dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    logger.info("GET /graph from %s", client)
    graph = load_graph()
    return graph_payload(graph)


@app.post("/seed")
def reseed(request: Request) -> Dict[str, str]:
    client = request.client.host if request.client else "unknown"
    logger.info("POST /seed from %s", client)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM edges")
    cur.execute("DELETE FROM nodes")
    seed_sample(conn)
    conn.close()
    return {"status": "ok"}


@app.get("/predict")
def predict_paths(
    request: Request,
    start: str = Query(..., description="Starting node id"),
    target: Optional[str] = Query(None, description="Target node id"),
    max_len: int = Query(6, ge=2, le=10)
) -> Dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    logger.info(
        "GET /predict from %s start=%s target=%s max_len=%s",
        client,
        start,
        target,
        max_len
    )
    graph = load_graph()
    if start not in graph.nodes:
        return {"paths": [], "next_steps": []}

    next_steps = [
        {
            "source": start,
            "target": neighbor,
            "prob": float(graph.get_edge_data(start, neighbor).get("prob", 0.1))
        }
        for neighbor in graph.successors(start)
    ]
    next_steps.sort(key=lambda item: item["prob"], reverse=True)

    if target and target in graph.nodes:
        paths = []
        for path in nx.all_simple_paths(graph, start, target, cutoff=max_len):
            score = score_path(graph, path)
            paths.append({"nodes": path, "score": score})
        paths.sort(key=lambda item: item["score"], reverse=True)
        return {"paths": paths[:5], "next_steps": next_steps}

    # If no target, return the shortest paths to all goals
    goal_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "goal"]
    suggestions = []
    for goal in goal_nodes:
        for path in nx.all_simple_paths(graph, start, goal, cutoff=max_len):
            suggestions.append({"target": goal, "nodes": path, "score": score_path(graph, path)})
    suggestions.sort(key=lambda item: item["score"], reverse=True)
    return {"paths": suggestions[:5], "next_steps": next_steps}


@app.post("/predict/paths")
def predict_paths_from_payload(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    start = payload.get("start")
    technique_filter = payload.get("technique")
    feature_filter = payload.get("feature")
    max_len = int(payload.get("max_len", 8))
    graph_payload_data = payload.get("graph") or {}
    if not start:
        logger.info("POST /predict/paths payload=%s response=empty_start", payload)
        return {"paths": []}
    graph = build_graph_from_payload(graph_payload_data)
    if start not in graph.nodes:
        logger.info("POST /predict/paths payload=%s response=start_not_found", payload)
        return {"paths": []}
    targets = [
        node_id
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "asset"
    ]
    paths = []
    for target in targets:
        for path in nx.all_simple_paths(graph, start, target, cutoff=max_len):
            risk_override = None
            if technique_filter:
                if len(path) < 2:
                    risk_override = 0.0
                else:
                    next_node = graph.nodes.get(path[1], {})
                    allowed = next_node.get("techniques") or []
                    if technique_filter not in allowed:
                        risk_override = 0.0
            if feature_filter:
                has_feature = False
                for node_id in path:
                    node_data = graph.nodes.get(node_id, {})
                    features = node_data.get("features") or []
                    if feature_filter in features:
                        has_feature = True
                        break
                if not has_feature:
                    continue
            paths.append(
                {
                    "nodes": path,
                    "risk": risk_override if risk_override is not None else score_path(graph, path),
                    "target": target,
                }
            )
    paths.sort(key=lambda item: item["risk"], reverse=True)
    response = {"paths": paths}
    logger.info("POST /predict/paths payload=%s response_paths=%s", payload, len(paths))
    return response


@app.post("/detection")
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


active_detection_sockets: set[WebSocket] = set()


@app.websocket("/ws/detection")
async def detection_socket(ws: WebSocket) -> None:
    await ws.accept()
    active_detection_sockets.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        active_detection_sockets.discard(ws)


@app.get("/mitre/tactics")
def get_mitre_tactics() -> Dict[str, Any]:
    if not MITRE_DB_PATH.exists():
        return {"tactics": []}
    conn = get_mitre_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT tactic_id, name, shortname FROM tactics ORDER BY order_index, name"
    ).fetchall()
    conn.close()
    return {
        "tactics": [
            {"tactic_id": row["tactic_id"], "name": row["name"], "shortname": row["shortname"]}
            for row in rows
        ]
    }


@app.get("/mitre/techniques")
def get_mitre_techniques(tactic: Optional[str] = None) -> Dict[str, Any]:
    if not MITRE_DB_PATH.exists():
        return {"techniques": []}
    conn = get_mitre_conn()
    cur = conn.cursor()
    if tactic:
        rows = cur.execute(
            """
            SELECT techniques.technique_id, techniques.name
            FROM techniques
            JOIN tactic_techniques ON tactic_techniques.technique_id = techniques.technique_id
            JOIN tactics ON tactics.tactic_id = tactic_techniques.tactic_id
            WHERE tactics.shortname = ?
              AND techniques.technique_id NOT LIKE '%.%'
            ORDER BY techniques.name
            """,
            (tactic,),
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT technique_id, name FROM techniques WHERE technique_id NOT LIKE '%.%' ORDER BY name"
        ).fetchall()
    conn.close()
    return {
        "techniques": [
            {"technique_id": row["technique_id"], "name": row["name"]}
            for row in rows
        ]
    }
