from __future__ import annotations

import os
from pathlib import Path
import logging

from fastapi import APIRouter
from peewee import AutoField, IntegerField, Model, SqliteDatabase, TextField

BASE_DIR = Path("/app/")
DATA_DIR = BASE_DIR / "data"
ATTACK_SCENARIO_DB_PATH = Path(
    os.environ.get("ATTACK_SCENARIO_DB_PATH", DATA_DIR / "attack_scenario.db")
)

logger = logging.getLogger("uvicorn.error")

database = SqliteDatabase(ATTACK_SCENARIO_DB_PATH)
router = APIRouter()


class BaseModel(Model):
    class Meta:
        database = database


class AttackScenario(BaseModel):
    id = AutoField()
    name = TextField()

    class Meta:
        table_name = "attack_scenarios"


class AttackScenarioStep(BaseModel):
    id = AutoField()
    scenairo_id = IntegerField(column_name="scenairo_id")
    order = IntegerField(column_name="order")
    technquename = TextField()

    class Meta:
        table_name = "attack_scenario_steps"


def fetch_scenario_steps(scenario_id: int) -> list[str]:
    """シナリオIDに紐づくテクニックの順序付きリストを返す。"""
    if not ATTACK_SCENARIO_DB_PATH.exists():
        return []
    database.connect(reuse_if_open=True)
    try:
        query = (
            AttackScenarioStep.select(AttackScenarioStep.technquename)
            .where(AttackScenarioStep.scenairo_id == scenario_id)
            .order_by(AttackScenarioStep.order)
        )
        return [row.technquename for row in query]
    finally:
        if not database.is_closed():
            database.close()


def fetch_all_scenarios() -> list[dict[str, int | str]]:
    """登録済みシナリオ一覧を返す。"""
    if not ATTACK_SCENARIO_DB_PATH.exists():
        logger.warning(f"DB file {ATTACK_SCENARIO_DB_PATH} is not found")
        return []
    database.connect(reuse_if_open=True)
    try:
        query = AttackScenario.select(AttackScenario.id, AttackScenario.name).order_by(
            AttackScenario.id
        )
        return [{"id": row.id, "name": row.name} for row in query]
    except Exception as e:
        logger.error(e)
        return []
    finally:
        if not database.is_closed():
            database.close()


@router.get("/scenario")
def get_attack_scenario(scenario_id: int) -> dict[str, list[str] | str]:
    """シナリオIDに紐づくテクニック一覧を返す。"""
    steps = fetch_scenario_steps(scenario_id)
    if steps:
        return {"status": "success", "scenario": steps}
    return {"status": "not_found", "scenario": []}


@router.get("/scenarios")
def list_attack_scenarios() -> dict[str, str | list[dict[str, int | str]]]:
    """登録済みシナリオ一覧を返す。"""
    return {"status": "success", "scenarios": fetch_all_scenarios()}
