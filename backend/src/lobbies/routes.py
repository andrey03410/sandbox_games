import json

from fastapi import APIRouter, Depends
from sqlalchemy import text

from src.auth.dependencies import current_user_id
from src.core.db import engine
from src.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from src.games.registry import get_game
from src.lobbies.schemas.create_lobby_request import CreateLobbyRequest
from src.lobbies.schemas.join_request import JoinRequest
from src.lobbies.schemas.move_request import MoveRequest
from src.lobbies.service import (
    active_games,
    broadcast_snapshot,
    build_snapshot,
    get_lobby_row,
    status_id,
)

router = APIRouter(prefix="/api/lobbies", tags=["lobbies"])

VALID_ROLES = {"player", "spectator"}


@router.get("")
def list_lobbies():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                l.id, l.name, l.created_by, l.config, l.max_players, l.created_at,
                g.code AS game_code, g.name AS game_name, g.config_schema,
                s.code AS status_code, s.name AS status_name,
                (SELECT login FROM users WHERE id = l.created_by) AS creator_login,
                COALESCE(
                    (SELECT COUNT(*) FROM lobby_participants
                     WHERE lobby_id = l.id AND role IN ('host','player')),
                    0
                ) AS players_count
            FROM lobbies l
            JOIN games          g ON g.id = l.game_id
            JOIN lobby_statuses s ON s.id = l.status_id
            ORDER BY l.id DESC
        """)).all()
    return [dict(r._mapping) for r in rows]


@router.post("", status_code=201)
async def create_lobby(
    req: CreateLobbyRequest, user_id: int = Depends(current_user_id)
):
    with engine.begin() as conn:
        game = conn.execute(
            text("SELECT id FROM games WHERE code = :code"),
            {"code": req.game_code},
        ).first()
        if game is None:
            raise BadRequest(f"unknown game_code: {req.game_code}")
        waiting_id = status_id(conn, "waiting")
        new_id = conn.execute(
            text("""
                INSERT INTO lobbies (name, game_id, status_id, created_by, config, max_players)
                VALUES (:name, :game_id, :status_id, :created_by, CAST(:config AS JSONB), :max_players)
                RETURNING id
            """),
            {
                "name": req.name,
                "game_id": game.id,
                "status_id": waiting_id,
                "created_by": user_id,
                "config": json.dumps(req.config),
                "max_players": req.max_players,
            },
        ).scalar_one()
        conn.execute(
            text("""
                INSERT INTO lobby_participants (lobby_id, user_id, role)
                VALUES (:lobby_id, :user_id, 'host')
            """),
            {"lobby_id": new_id, "user_id": user_id},
        )
    return {"id": new_id}


@router.get("/{lobby_id}")
def get_lobby(lobby_id: int, user_id: int = Depends(current_user_id)):
    snapshot = build_snapshot(lobby_id)
    if snapshot is None:
        raise NotFound("lobby not found")
    return snapshot


@router.post("/{lobby_id}/join")
async def join_lobby(
    lobby_id: int,
    req: JoinRequest,
    user_id: int = Depends(current_user_id),
):
    if req.role not in VALID_ROLES:
        raise BadRequest("invalid role")

    with engine.begin() as conn:
        row = get_lobby_row(conn, lobby_id)
        if row is None:
            raise NotFound("lobby not found")

        existing = conn.execute(
            text("""
                SELECT role FROM lobby_participants
                WHERE lobby_id = :lid AND user_id = :uid
            """),
            {"lid": lobby_id, "uid": user_id},
        ).first()
        if existing is not None:
            if existing.role == "host":
                raise BadRequest("you are the host")
            if existing.role != req.role:
                conn.execute(
                    text("""
                        UPDATE lobby_participants SET role = :r
                        WHERE lobby_id = :lid AND user_id = :uid
                    """),
                    {"r": req.role, "lid": lobby_id, "uid": user_id},
                )
        else:
            if req.role == "player":
                max_players = int(row.config_schema.get("max_players", row.max_players))
                taken = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM lobby_participants
                        WHERE lobby_id = :lid AND role IN ('host','player')
                    """),
                    {"lid": lobby_id},
                ).scalar_one()
                if taken >= max_players:
                    raise Conflict("no free player slot")
            conn.execute(
                text("""
                    INSERT INTO lobby_participants (lobby_id, user_id, role)
                    VALUES (:lid, :uid, :r)
                """),
                {"lid": lobby_id, "uid": user_id, "r": req.role},
            )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/leave")
async def leave_lobby(lobby_id: int, user_id: int = Depends(current_user_id)):
    with engine.begin() as conn:
        row = get_lobby_row(conn, lobby_id)
        if row is None:
            raise NotFound("lobby not found")
        if row.created_by == user_id:
            raise BadRequest("host cannot leave")
        conn.execute(
            text("""
                DELETE FROM lobby_participants
                WHERE lobby_id = :lid AND user_id = :uid
            """),
            {"lid": lobby_id, "uid": user_id},
        )
    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/start")
async def start_game(lobby_id: int, user_id: int = Depends(current_user_id)):
    with engine.begin() as conn:
        row = get_lobby_row(conn, lobby_id)
        if row is None:
            raise NotFound("lobby not found")
        if row.created_by != user_id:
            raise Forbidden("only host can start")
        if row.status_code != "waiting":
            raise BadRequest("game already started or finished")

        players = conn.execute(
            text("""
                SELECT user_id FROM lobby_participants
                WHERE lobby_id = :lid AND role IN ('host','player')
                ORDER BY joined_at
            """),
            {"lid": lobby_id},
        ).all()
        player_ids = [p.user_id for p in players]

        min_players = int(row.config_schema.get("min_players", 2))
        max_players = int(row.config_schema.get("max_players", min_players))
        if len(player_ids) < min_players:
            raise BadRequest(f"not enough players: {len(player_ids)}/{min_players}")

        game = get_game(row.game_code)
        if game is None:
            raise BadRequest(f"unsupported game: {row.game_code}")
        state = game.init_state(row.config, player_ids[:max_players])

        active_games[lobby_id] = state
        conn.execute(
            text("UPDATE lobbies SET status_id = :sid WHERE id = :id"),
            {"sid": status_id(conn, "in_progress"), "id": lobby_id},
        )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/move")
async def make_move(
    lobby_id: int,
    req: MoveRequest,
    user_id: int = Depends(current_user_id),
):
    state = active_games.get(lobby_id)
    if state is None:
        raise NotFound("no active game")
    game = get_game(state["game_code"])
    if game is None:
        raise RuntimeError(f"game impl missing: {state['game_code']}")
    game.apply_move(state, user_id, req.model_dump())

    if state["status"] == "finished":
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE lobbies SET status_id = :sid WHERE id = :id"),
                {"sid": status_id(conn, "finished"), "id": lobby_id},
            )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}
