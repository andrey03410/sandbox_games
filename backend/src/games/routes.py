from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.db import get_session
from src.games.models import Game

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
def list_games(session: Session = Depends(get_session)):
    rows = session.execute(
        select(Game.id, Game.code, Game.name, Game.config_schema).order_by(Game.id)
    ).all()
    return [dict(r._mapping) for r in rows]
