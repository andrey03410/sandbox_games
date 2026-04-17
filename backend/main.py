import asyncio
import json
from collections import defaultdict

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

import tic_tac_toe
from auth import (
    create_token,
    current_user_id,
    decode_token,
    hash_password,
    verify_password,
)

DATABASE_URL = "postgresql://gameuser:gamepass@localhost:5433/gamedb"
engine = create_engine(DATABASE_URL)

AVATAR_CODES = {"nebula", "flame", "leaf", "wave", "crown", "moon"}
VALID_ROLES = {"player", "spectator"}

active_games: dict[int, dict] = {}

lobby_rooms: dict[int, set[WebSocket]] = defaultdict(set)
rooms_lock = asyncio.Lock()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=200)
    avatar: str = "nebula"


class LoginRequest(BaseModel):
    login: str
    password: str


class CreateLobbyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    game_code: str
    config: dict = {}
    max_players: int = Field(default=10, ge=1, le=100)


class JoinRequest(BaseModel):
    role: str


class MoveRequest(BaseModel):
    row: int
    col: int


def _serialize_user(row) -> dict:
    return {
        "id": row.id,
        "login": row.login,
        "avatar": row.avatar,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _status_id(conn, code: str) -> int:
    row = conn.execute(
        text("SELECT id FROM lobby_statuses WHERE code = :c"), {"c": code}
    ).first()
    if row is None:
        raise HTTPException(status_code=500, detail=f"status '{code}' missing")
    return row.id


def _get_lobby_row(conn, lobby_id: int):
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


def _get_participants(conn, lobby_id: int) -> list[dict]:
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


def _serialize_lobby(row, participants: list[dict]) -> dict:
    players = [p for p in participants if p["role"] in ("host", "player")]
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
        row = _get_lobby_row(conn, lobby_id)
        if row is None:
            return None
        participants = _get_participants(conn, lobby_id)
    return {
        "lobby": _serialize_lobby(row, participants),
        "participants": participants,
        "game_state": active_games.get(lobby_id),
    }


async def broadcast_snapshot(lobby_id: int) -> None:
    snapshot = build_snapshot(lobby_id)
    if snapshot is None:
        return
    payload = {"type": "snapshot", "data": snapshot}
    async with rooms_lock:
        targets = list(lobby_rooms.get(lobby_id, ()))
    dead: list[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    if dead:
        async with rooms_lock:
            room = lobby_rooms.get(lobby_id)
            if room is not None:
                for ws in dead:
                    room.discard(ws)


@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest):
    if req.avatar not in AVATAR_CODES:
        raise HTTPException(status_code=400, detail=f"unknown avatar: {req.avatar}")
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE login = :login"),
            {"login": req.login},
        ).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="login already taken")
        row = conn.execute(
            text("""
                INSERT INTO users (login, password_hash, avatar)
                VALUES (:login, :hash, :avatar)
                RETURNING id, login, avatar, created_at
            """),
            {
                "login": req.login,
                "hash": hash_password(req.password),
                "avatar": req.avatar,
            },
        ).first()
    return {"token": create_token(row.id), "user": _serialize_user(row)}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, login, password_hash, avatar, created_at
                FROM users WHERE login = :login
            """),
            {"login": req.login},
        ).first()
    if row is None or not verify_password(req.password, row.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_token(row.id), "user": _serialize_user(row)}


@app.get("/api/auth/me")
def me(user_id: int = Depends(current_user_id)):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, login, avatar, created_at FROM users WHERE id = :id"),
            {"id": user_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _serialize_user(row)


@app.get("/api/games")
def list_games():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, code, name, config_schema FROM games ORDER BY id")
        )
        return [dict(row._mapping) for row in result]


@app.get("/api/lobbies")
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


@app.post("/api/lobbies", status_code=201)
async def create_lobby(req: CreateLobbyRequest, user_id: int = Depends(current_user_id)):
    with engine.begin() as conn:
        game = conn.execute(
            text("SELECT id FROM games WHERE code = :code"),
            {"code": req.game_code},
        ).first()
        if game is None:
            raise HTTPException(status_code=400, detail=f"unknown game_code: {req.game_code}")
        waiting_id = _status_id(conn, "waiting")
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


@app.get("/api/lobbies/{lobby_id}")
def get_lobby(lobby_id: int, user_id: int = Depends(current_user_id)):
    snapshot = build_snapshot(lobby_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="lobby not found")
    return snapshot


@app.post("/api/lobbies/{lobby_id}/join")
async def join_lobby(
    lobby_id: int,
    req: JoinRequest,
    user_id: int = Depends(current_user_id),
):
    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")

    with engine.begin() as conn:
        row = _get_lobby_row(conn, lobby_id)
        if row is None:
            raise HTTPException(status_code=404, detail="lobby not found")

        existing = conn.execute(
            text("""
                SELECT role FROM lobby_participants
                WHERE lobby_id = :lid AND user_id = :uid
            """),
            {"lid": lobby_id, "uid": user_id},
        ).first()
        if existing is not None:
            if existing.role == "host":
                raise HTTPException(status_code=400, detail="you are the host")
            if existing.role == req.role:
                pass
            else:
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
                    raise HTTPException(status_code=409, detail="no free player slot")
            conn.execute(
                text("""
                    INSERT INTO lobby_participants (lobby_id, user_id, role)
                    VALUES (:lid, :uid, :r)
                """),
                {"lid": lobby_id, "uid": user_id, "r": req.role},
            )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@app.post("/api/lobbies/{lobby_id}/leave")
async def leave_lobby(lobby_id: int, user_id: int = Depends(current_user_id)):
    with engine.begin() as conn:
        row = _get_lobby_row(conn, lobby_id)
        if row is None:
            raise HTTPException(status_code=404, detail="lobby not found")
        if row.created_by == user_id:
            raise HTTPException(status_code=400, detail="host cannot leave")
        conn.execute(
            text("""
                DELETE FROM lobby_participants
                WHERE lobby_id = :lid AND user_id = :uid
            """),
            {"lid": lobby_id, "uid": user_id},
        )
    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@app.post("/api/lobbies/{lobby_id}/start")
async def start_game(lobby_id: int, user_id: int = Depends(current_user_id)):
    with engine.begin() as conn:
        row = _get_lobby_row(conn, lobby_id)
        if row is None:
            raise HTTPException(status_code=404, detail="lobby not found")
        if row.created_by != user_id:
            raise HTTPException(status_code=403, detail="only host can start")
        if row.status_code != "waiting":
            raise HTTPException(status_code=400, detail="game already started or finished")

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
        if len(player_ids) < min_players:
            raise HTTPException(
                status_code=400,
                detail=f"not enough players: {len(player_ids)}/{min_players}",
            )

        if row.game_code == "tic_tac_toe":
            state = tic_tac_toe.init_state(row.config, player_ids[:2])
        else:
            raise HTTPException(status_code=400, detail=f"unsupported game: {row.game_code}")

        active_games[lobby_id] = state
        conn.execute(
            text("UPDATE lobbies SET status_id = :sid WHERE id = :id"),
            {"sid": _status_id(conn, "in_progress"), "id": lobby_id},
        )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@app.post("/api/lobbies/{lobby_id}/move")
async def make_move(
    lobby_id: int,
    req: MoveRequest,
    user_id: int = Depends(current_user_id),
):
    state = active_games.get(lobby_id)
    if state is None:
        raise HTTPException(status_code=404, detail="no active game")
    try:
        tic_tac_toe.apply_move(state, user_id, req.row, req.col)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if state["status"] == "finished":
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE lobbies SET status_id = :sid WHERE id = :id"),
                {"sid": _status_id(conn, "finished"), "id": lobby_id},
            )

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@app.websocket("/ws/lobby/{lobby_id}")
async def ws_lobby(
    websocket: WebSocket,
    lobby_id: int,
    token: str | None = Query(default=None),
):
    if not token:
        await websocket.close(code=4401)
        return
    try:
        decode_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    async with rooms_lock:
        lobby_rooms[lobby_id].add(websocket)

    try:
        snapshot = build_snapshot(lobby_id)
        if snapshot is None:
            await websocket.send_json({"type": "error", "detail": "lobby not found"})
            await websocket.close()
            return
        await websocket.send_json({"type": "snapshot", "data": snapshot})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with rooms_lock:
            room = lobby_rooms.get(lobby_id)
            if room is not None:
                room.discard(websocket)
                if not room:
                    lobby_rooms.pop(lobby_id, None)


@app.websocket("/ws")
async def websocket_lobbies_list(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "get_lobbies":
                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT
                            l.id, l.name, l.max_players,
                            g.code AS game_code, g.name AS game_name,
                            s.code AS status_code, s.name AS status_name,
                            COALESCE(
                                (SELECT COUNT(*) FROM lobby_participants
                                 WHERE lobby_id = l.id AND role IN ('host','player')),
                                0
                            ) AS players_count,
                            l.config
                        FROM lobbies l
                        JOIN games          g ON g.id = l.game_id
                        JOIN lobby_statuses s ON s.id = l.status_id
                        ORDER BY l.id DESC
                    """)).all()
                    lobbies = [dict(r._mapping) for r in rows]
                await websocket.send_json({"type": "lobbies_list", "data": lobbies})
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
