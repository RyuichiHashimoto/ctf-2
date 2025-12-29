from __future__ import annotations

import os
from pathlib import Path
from typing_extensions import TypedDict

from fastapi import APIRouter
from peewee import (
    AutoField,
    CompositeKey,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)
import logging

BASE_DIR = Path("/app/")
DATA_DIR = BASE_DIR / "data"
MITRE_DB_PATH = Path(os.environ.get("MITRE_DB_PATH", DATA_DIR / "mitre_attack.db"))

print("file found: ", MITRE_DB_PATH.exists(), MITRE_DB_PATH)


router = APIRouter()
logger = logging.getLogger("uvicorn.error")
database = SqliteDatabase(MITRE_DB_PATH)

class TechniqueItem(TypedDict):
    technique_id: str
    name: str

class TacticItem(TypedDict):
    tactic_id: str
    name: str
    shortname: str


class BaseModel(Model):
    class Meta:
        database = database


class Technique(BaseModel):
    id = AutoField()
    technique_id = TextField(unique=True)
    name = TextField()
    description = TextField()

    class Meta:
        table_name = "techniques"


class Tactic(BaseModel):
    id = AutoField()
    tactic_id = TextField(unique=True)
    name = TextField()
    shortname = TextField(unique=True)
    order_index = IntegerField()

    class Meta:
        table_name = "tactics"


class TacticTechnique(BaseModel):
    tactic_id = TextField()
    technique_id = TextField()

    class Meta:
        table_name = "tactic_techniques"
        primary_key = CompositeKey("tactic_id", "technique_id")


def fetch_techniques_by_tactic(tactic: str) -> list[TechniqueItem]:
    """指定タクティクに紐づくテクニック一覧を取得する。"""
    query = (
        Technique.select(Technique.technique_id, Technique.name)
        .join(TacticTechnique, on=(TacticTechnique.technique_id == Technique.technique_id))
        .join(Tactic, on=(Tactic.tactic_id == TacticTechnique.tactic_id))
        .where((Tactic.shortname == tactic) & ~(Technique.technique_id ** '%.%'))
        .order_by(Technique.name)
    )
    return [
        {"technique_id": row.technique_id, "name": row.name}
        for row in query
    ]


def fetch_all_techniques() -> list[TechniqueItem]:
    """全テクニック（サブテクニック除外）を取得する。"""
    query = (
        Technique.select(Technique.technique_id, Technique.name)
        .where(~(Technique.technique_id ** '%.%'))
        .order_by(Technique.name)
    )
    return [
        {"technique_id": row.technique_id, "name": row.name}
        for row in query
    ]


def fetch_all_tactics() -> list[TacticItem]:
    """全タクティクを取得する。"""
    query = (
        Tactic.select(Tactic.tactic_id, Tactic.name, Tactic.shortname)
        .order_by(Tactic.order_index, Tactic.name)
    )
    return [
        {"tactic_id": row.tactic_id, "name": row.name, "shortname": row.shortname}
        for row in query
    ]


@router.get("/mitre/tactics")
def get_mitre_tactics() -> dict[str, list[TacticItem]]:
    """MITRE ATT&CKのタクティク一覧を返す。"""
    if not MITRE_DB_PATH.exists():
        return {"tactics": []}
    database.connect(reuse_if_open=True)
    try:
        rows = fetch_all_tactics()
    finally:
        if not database.is_closed():
            database.close()
    return {
        "tactics": rows
    }


@router.get("/mitre/techniques")
def get_mitre_techniques(tactic: str | None = None) -> dict[str, list[TechniqueItem]]:
    """MITRE ATT&CKのテクニック一覧を返す。"""
    if not MITRE_DB_PATH.exists():
        return {"techniques": []}
    database.connect(reuse_if_open=True)
    try:
        if tactic:
            rows = fetch_techniques_by_tactic(tactic)
        else:
            rows = fetch_all_techniques()
    finally:
        if not database.is_closed():
            database.close()
    return {"techniques": rows}
