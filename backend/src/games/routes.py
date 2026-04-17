from fastapi import APIRouter
from sqlalchemy import text

from src.core.db import engine

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
def list_games():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, code, name, config_schema FROM games ORDER BY id")
        ).all()
    return [dict(r._mapping) for r in rows]
