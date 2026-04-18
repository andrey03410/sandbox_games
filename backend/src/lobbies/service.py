from dataclasses import asdict

from sqlalchemy import text

from src.core.db import engine
from src.core.ws.lobby_ws_manager import lobby_ws_manager
from src.games.state import BaseState
from src.lobbies.enums import ParticipantRole

active_games: dict[int, BaseState] = {}


def status_id(conn, code: str) -> int:
    row = conn.execute(
        text("SELECT id FROM lobby_statuses WHERE code = :c"), {"c": code}
    ).first()
    if row is None:
        raise RuntimeError(f"status '{code}' missing in lobby_statuses seed")
    return row.id


def get_lobby_row(conn, lobby_id: int):
    return conn.execute(
        text("""
            SELECT
                l.id, l.name, l.created_by, l.config, l.max_players,
                l.created_at,
                g.code AS game_code, g.name AS game_name, g.config_schema,
                s.code AS status_code, s.name AS status_name,
                (SELECT login FROM users WHERE id = l.created_by) AS creator_login
            FROM lobbies l
            JOIN games          g ON g.id = l.game_id
            JOIN lobby_statuses s ON s.id = l.status_id
            WHERE l.id = :id
        """),
        {"id": lobby_id},
    ).first()


def get_participants(conn, lobby_id: int) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT p.user_id, p.role, p.joined_at, u.login, u.avatar
            FROM lobby_participants p
            JOIN users u ON u.id = p.user_id
            WHERE p.lobby_id = :id
            ORDER BY p.joined_at
        """),
        {"id": lobby_id},
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
    with engine.connect() as conn:
        row = get_lobby_row(conn, lobby_id)
        if row is None:
            return None
        participants = get_participants(conn, lobby_id)
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
