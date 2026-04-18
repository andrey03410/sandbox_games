from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.auth.models import User
from src.core.db import SessionLocal
from src.core.ws.lobby_ws_manager import lobby_ws_manager
from src.games.models import Game
from src.games.state import BaseState
from src.lobbies.enums import ParticipantRole
from src.lobbies.models import Lobby, LobbyParticipant, LobbyStatus

active_games: dict[int, BaseState] = {}


def status_id(session: Session, code: str) -> int:
    sid = session.scalar(select(LobbyStatus.id).where(LobbyStatus.code == code))
    if sid is None:
        raise RuntimeError(f"status '{code}' missing in lobby_statuses seed")
    return sid


LOBBY_VIEW_COLUMNS = (
    Lobby.id,
    Lobby.name,
    Lobby.created_by,
    Lobby.config,
    Lobby.max_players,
    Lobby.created_at,
    Game.code.label("game_code"),
    Game.name.label("game_name"),
    Game.config_schema,
    LobbyStatus.code.label("status_code"),
    LobbyStatus.name.label("status_name"),
    User.login.label("creator_login"),
)


def _lobby_view_stmt():
    return (
        select(*LOBBY_VIEW_COLUMNS)
        .join(Game, Game.id == Lobby.game_id)
        .join(LobbyStatus, LobbyStatus.id == Lobby.status_id)
        .join(User, User.id == Lobby.created_by)
    )


def get_lobby_row(session: Session, lobby_id: int):
    return session.execute(
        _lobby_view_stmt().where(Lobby.id == lobby_id)
    ).first()


def count_active_participants(session: Session, lobby_id: int) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(LobbyParticipant)
            .where(
                LobbyParticipant.lobby_id == lobby_id,
                LobbyParticipant.role.in_(
                    [ParticipantRole.HOST, ParticipantRole.PLAYER]
                ),
            )
        )
        or 0
    )


def list_lobby_views(session: Session) -> list[dict]:
    rows = session.execute(
        _lobby_view_stmt().order_by(Lobby.id.desc())
    ).all()
    return [
        {
            **dict(r._mapping),
            "players_count": count_active_participants(session, r.id),
        }
        for r in rows
    ]


def get_participants(session: Session, lobby_id: int) -> list[dict]:
    rows = session.execute(
        select(
            LobbyParticipant.user_id,
            LobbyParticipant.role,
            LobbyParticipant.joined_at,
            User.login,
            User.avatar,
        )
        .join(User, User.id == LobbyParticipant.user_id)
        .where(LobbyParticipant.lobby_id == lobby_id)
        .order_by(LobbyParticipant.joined_at)
    ).all()
    return [
        {
            "user_id": r.user_id,
            "login": r.login,
            "avatar": r.avatar,
            "role": r.role,
            "joined_at": r.joined_at.isoformat() if r.joined_at else None,
        }
        for r in rows
    ]


def serialize_lobby(row, participants: list[dict]) -> dict:
    players = [
        p for p in participants
        if p["role"] in (ParticipantRole.HOST, ParticipantRole.PLAYER)
    ]
    return {
        "id": row.id,
        "name": row.name,
        "game_code": row.game_code,
        "game_name": row.game_name,
        "config_schema": row.config_schema,
        "config": row.config,
        "max_players": row.max_players,
        "status_code": row.status_code,
        "status_name": row.status_name,
        "created_by": row.created_by,
        "creator_login": row.creator_login,
        "players_count": len(players),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def build_snapshot(lobby_id: int) -> dict | None:
    with SessionLocal() as session:
        row = get_lobby_row(session, lobby_id)
        if row is None:
            return None
        participants = get_participants(session, lobby_id)
    state = active_games.get(lobby_id)
    return {
        "lobby": serialize_lobby(row, participants),
        "participants": participants,
        "game_state": asdict(state) if state is not None else None,
    }


async def broadcast_snapshot(lobby_id: int) -> None:
    snapshot = build_snapshot(lobby_id)
    if snapshot is None:
        return
    await lobby_ws_manager.broadcast(lobby_id, {"type": "snapshot", "data": snapshot})
