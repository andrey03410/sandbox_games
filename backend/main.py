from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import json

DATABASE_URL = "postgresql://gameuser:gamepass@localhost:5433/gamedb"
engine = create_engine(DATABASE_URL)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_lobbies():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, name, game_type, players_count, max_players, status
            FROM lobbies
        """))
        return [
            {
                "id": row.id,
                "name": row.name,
                "game_type": row.game_type,
                "players_count": row.players_count,
                "max_players": row.max_players,
                "status": row.status,
            }
            for row in result
        ]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "get_lobbies":
                lobbies = get_lobbies()
                await websocket.send_json({
                    "type": "lobbies_list",
                    "data": lobbies
                })
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
