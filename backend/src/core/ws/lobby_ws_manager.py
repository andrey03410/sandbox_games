import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)


class LobbyWSManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, lobby_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[lobby_id].add(ws)
            size = len(self._rooms[lobby_id])
        logger.info("ws connect lobby=%s subscribers=%s", lobby_id, size)

    async def disconnect(self, lobby_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(lobby_id)
            if room is None:
                return
            room.discard(ws)
            size = len(room)
            if not room:
                self._rooms.pop(lobby_id, None)
        logger.info("ws disconnect lobby=%s subscribers=%s", lobby_id, size)

    async def broadcast(self, lobby_id: int, payload: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(lobby_id, ()))
        serialized = jsonable_encoder(payload)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(serialized)
            except Exception:
                dead.append(ws)
        logger.debug(
            "ws broadcast lobby=%s type=%s sent=%s dead=%s",
            lobby_id, payload.get("type"), len(targets) - len(dead), len(dead),
        )
        if dead:
            async with self._lock:
                room = self._rooms.get(lobby_id)
                if room is not None:
                    for ws in dead:
                        room.discard(ws)


lobby_ws_manager = LobbyWSManager()
