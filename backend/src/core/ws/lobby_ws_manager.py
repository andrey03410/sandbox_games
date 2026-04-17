import asyncio
from collections import defaultdict

from fastapi import WebSocket


class LobbyWSManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, lobby_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[lobby_id].add(ws)

    async def disconnect(self, lobby_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(lobby_id)
            if room is None:
                return
            room.discard(ws)
            if not room:
                self._rooms.pop(lobby_id, None)

    async def broadcast(self, lobby_id: int, payload: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(lobby_id, ()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                room = self._rooms.get(lobby_id)
                if room is not None:
                    for ws in dead:
                        room.discard(ws)


lobby_ws_manager = LobbyWSManager()
