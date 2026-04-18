import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from src.auth.jwt_service import decode_token
from src.core.db import SessionLocal
from src.core.exceptions import Unauthorized
from src.core.ws.lobby_ws_manager import lobby_ws_manager
from src.lobbies.service import build_snapshot, list_lobby_views

logger = logging.getLogger(__name__)

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
        await websocket.send_json(jsonable_encoder({"type": "snapshot", "data": snapshot}))
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
                with SessionLocal() as session:
                    lobbies = list_lobby_views(session)
                await websocket.send_json(
                    jsonable_encoder({"type": "lobbies_list", "data": lobbies})
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws /ws handler failed")
        await websocket.close(code=1011)
