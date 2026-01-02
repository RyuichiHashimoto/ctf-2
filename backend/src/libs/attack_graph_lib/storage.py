import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Dict, Iterator, List, Sequence

import networkx as nx
from peewee import AutoField, ForeignKeyField, Model, SqliteDatabase, TextField, FloatField

from .schema import GraphData, load_graph_from_json_path

BASE_DIR = Path("/app")
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "attack_graph.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DB_PATH = UPLOAD_DIR / "uploads.db"
database = SqliteDatabase(DB_PATH, pragmas={"foreign_keys": 1})
upload_database = SqliteDatabase(UPLOAD_DB_PATH)


class BaseModel(Model):
    class Meta:
        database = database


class NodeModel(BaseModel):
    id = TextField(primary_key=True)
    label = TextField(primary_key=False, null=False)
    type = TextField(primary_key=False, null=False)
    techniques: List[str] = TextField()
    features: List[str] = TextField()


class EdgeModel(BaseModel):
    id = TextField(primary_key=True)
    source = ForeignKeyField(NodeModel, backref="out_edges", column_name="source")
    target = ForeignKeyField(NodeModel, backref="in_edges", column_name="target")
    risk = FloatField()


class ContainsModel(BaseModel):
    id = TextField(primary_key=True)
    parent = ForeignKeyField(NodeModel, backref="out_edges", column_name="source")
    child = ForeignKeyField(NodeModel, backref="in_edges", column_name="target")
    label = TextField()



class UploadBaseModel(Model):
    class Meta:
        database = upload_database


class UploadModel(UploadBaseModel):
    id = AutoField()
    file_uuid = TextField(null=False)
    filename = TextField(null=False)
    stored_json_name = TextField(null=False)
    stored_sqlite_name = TextField(null=False)
    uploaded_at = TextField(null=False)


@contextmanager
def sqlite_db_connection(path: Path | str, models = Sequence[type[Model]]) -> Iterator[SqliteDatabase]:
    """SQLite接続のコンテキスト。ファイルが無ければ作成する。"""
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()
    db = SqliteDatabase(db_path)
    db.connect(reuse_if_open=True)
    try:
        db.bind(list(models), bind_refs=False, bind_backrefs=False)
        existing = set(db.get_tables())
        missing = [
            model for model in models if model._meta.table_name not in existing
        ]
        if missing:
            db.create_tables(list(missing), safe=True)
        yield db
    finally:
        if not db.is_closed():
            db.close()

def normalize_graph_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "nodes" in payload and "edges" in payload:
        return {
            "nodes": payload.get("nodes") or [],
            "edges": payload.get("edges") or []
        }
    if "graph" in payload:
        graph = payload.get("graph") or {}
        nodes = [
            {
                "id": node.get("id"),
                "label": node.get("label") or node.get("labe;") or node.get("id"),
                "type": node.get("type") or "unknown",
                "techniques": node.get("techniques") or [],
                "features": node.get("features") or []
            }
            for node in (graph.get("node") or [])
            if node.get("id")
        ]
        edges = []
        for index, edge in enumerate((graph.get("edge") or []) + (graph.get("contains") or [])):
            edges.append(
                {
                    "id": edge.get("id") or f"edge-{index}",
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "prob": edge.get("prob", 0.1),
                    "technique": edge.get("technique", "")
                }
            )
        return {"nodes": nodes, "edges": edges}
    raise ValueError("Invalid graph format")


def seed_sample() -> None:
    sample_paths = [
        DATA_DIR / "sample_configuration_1.json",
        BASE_DIR.parent / "data" / "sample_configuration_1.json",
    ]
    sample_path = next((path for path in sample_paths if path.exists()), None)
    if not sample_path:
        return
    payload = json.loads(sample_path.read_text("utf-8"))
    normalized = normalize_graph_payload(payload)
    with database.atomic():
        for node in normalized.get("nodes", []):
            node_id = node.get("id")
            if not node_id:
                continue
            NodeModel.create(id=node_id, data_json=json.dumps(node))
        for edge in normalized.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue
            if not NodeModel.select().where(NodeModel.id == source).exists():
                continue
            if not NodeModel.select().where(NodeModel.id == target).exists():
                continue
            edge_id = edge.get("id") or f"{source}->{target}"
            EdgeModel.create(
                id=edge_id,
                source=source,
                target=target,
                data_json=json.dumps(edge),
            )


def save_graph(graph: GraphData, db_path: Path | str = DB_PATH) -> None:
    with sqlite_db_connection(db_path, [NodeModel, EdgeModel,ContainsModel]) as db:
        with db.atomic():
            EdgeModel.delete().execute()
            NodeModel.delete().execute()
            ContainsModel.delete().execute()
            
            node_rows: list[dict[str, Any]] = [node.asdict() for node in graph.nodes]
            if node_rows: NodeModel.insert_many(node_rows).execute()

            edge_rows: list[dict[str, Any]] = [edge.asdict() for edge in graph.edges]            
            if edge_rows: EdgeModel.insert_many(edge_rows).execute()

            contains_rows: list[dict[str, Any]] = [contain.asdict() for contain in graph.contains]
            if contains_rows: ContainsModel.insert_many(contains_rows).execute()

def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    database.connect(reuse_if_open=True)
    try:
        database.create_tables([NodeModel, EdgeModel])
        if NodeModel.select().count() == 0:
            seed_sample()
    finally:
        if not database.is_closed():
            database.close()
    init_upload_db()


def init_upload_db() -> None:
    """アップロード済みファイルのメタ情報DBを初期化する。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite_db_connection(UPLOAD_DB_PATH, [UploadModel]):
        pass


def record_upload(
    file_uuid: str,
    filename: str,
    stored_json_name: str,
    stored_sqlite_name: str,
) -> None:
    """アップロード済みファイルの対応関係を保存する。"""
    init_upload_db()
    with sqlite_db_connection(UPLOAD_DB_PATH, [UploadModel]) as db:
        UploadModel.insert(
            file_uuid=file_uuid,
            filename=filename,
            stored_json_name=stored_json_name,
            stored_sqlite_name=stored_sqlite_name,
            uploaded_at=datetime.now(timezone.utc).isoformat()
        ).on_conflict_replace().execute()


def list_uploads() -> List[Dict[str, str]]:
    """アップロード済みファイルの一覧を返す。"""
    if not UPLOAD_DB_PATH.exists():
        return []
    with sqlite_db_connection(UPLOAD_DB_PATH, [UploadModel]) as db:
        rows = (
            UploadModel
            .select(UploadModel.file_uuid, UploadModel.filename)
            .order_by(UploadModel.uploaded_at.desc())
        )
        return [
            {
                "file_id": row.file_uuid,
                "filename": row.filename,
            }
            for row in rows
        ]


def get_upload_record(file_uuid: str) -> Dict[str, str] | None:
    """アップロード済みファイルのメタ情報を取得する。"""
    if not UPLOAD_DB_PATH.exists():
        return None
    with sqlite_db_connection(UPLOAD_DB_PATH, [UploadModel]) as db:
        row = (
            UploadModel
            .select(
                UploadModel.file_uuid,
                UploadModel.filename,
                UploadModel.stored_json_name,
                UploadModel.stored_sqlite_name,
            )
            .where(UploadModel.file_uuid == file_uuid)
            .first()
        )
        if not row:
            return None
        return {
            "file_id": row.file_uuid,
            "filename": row.filename,
            "stored_json_name": row.stored_json_name,
            "stored_sqlite_name": row.stored_sqlite_name,
        }

def load_uploaded_graph_payload(file_uuid: str) -> GraphData:
    """アップロード済みJSONを読み込み、正規化済みデータを返す。"""
    
    record = get_upload_record(file_uuid)
    if not record:
        raise FileNotFoundError(file_uuid)
    target_path = UPLOAD_DIR / file_uuid / record["stored_json_name"]
    if not target_path.exists():
        raise FileNotFoundError(target_path)
    
    return load_graph_from_json_path(target_path)


def clear_uploads() -> int:
    """アップロード済みファイルとメタ情報DBを削除する。"""
    removed = 0
    if UPLOAD_DB_PATH.exists():
        UPLOAD_DB_PATH.unlink()
        removed += 1
    if UPLOAD_DIR.exists():
        for path in UPLOAD_DIR.iterdir():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
    return removed
