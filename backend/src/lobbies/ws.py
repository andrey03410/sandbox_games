import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from src.auth.jwt_service import decode_token
from src.core.db import engine
from src.core.exceptions import Unauthorized
from src.core.ws.lobby_ws_manager import lobby_ws_manager
from src.lobbies.enums import ParticipantRole
from src.lobbies.service import build_snapshot

router = APIRouter()


@router.websocket("/ws/lobby/{lobby_id}")
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
    except Unauthorized:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await lobby_ws_manager.connect(lobby_id, websocket)

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
        await lobby_ws_manager.disconnect(lobby_id, websocket)


@router.websocket("/ws")
async def ws_lobbies_list(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "get_lobbies":
                with engine.connect() as conn:
                    rows = conn.execute(
                        text("""
                            SELECT
                                l.id, l.name, l.max_players,
                                g.code AS game_code, g.name AS game_name,
                                s.code AS status_code, s.name AS status_name,
                                COALESCE(
                                    (SELECT COUNT(*) FROM lobby_participants
                                     WHERE lobby_id = l.id AND role IN (:host, :player)),
                                    0
                                ) AS players_count,
                                l.config
                            FROM lobbies l
                            JOIN games          g ON g.id = l.game_id
                            JOIN lobby_statuses s ON s.id = l.status_id
                            ORDER BY l.id DESC
                        """),
                        {
                            "host": ParticipantRole.HOST,
                            "player": ParticipantRole.PLAYER,
                        },
                    ).all()
                    lobbies = [dict(r._mapping) for r in rows]
                await websocket.send_json({"type": "lobbies_list", "data": lobbies})
    except Exception:
        pass
