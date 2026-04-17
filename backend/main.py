from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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


class CreateLobbyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    game_code: str
    config: dict = {}
    max_players: int = Field(default=10, ge=1, le=100)


def get_lobbies():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                l.id,
                l.name,
                g.code AS game_code,
                g.name AS game_name,
                l.config,
                l.players_count,
                l.max_players,
                s.code AS status_code,
                s.name AS status_name
            FROM lobbies l
            JOIN games          g ON g.id = l.game_id
            JOIN lobby_statuses s ON s.id = l.status_id
            ORDER BY l.id DESC
        """))
        return [dict(row._mapping) for row in result]


@app.get("/api/games")
def list_games():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, code, name, config_schema
            FROM games
            ORDER BY id
        """))
        return [dict(row._mapping) for row in result]


@app.get("/api/lobbies")
def list_lobbies():
    return get_lobbies()


@app.post("/api/lobbies", status_code=201)
def create_lobby(req: CreateLobbyRequest):
    with engine.begin() as conn:
        game = conn.execute(
            text("SELECT id FROM games WHERE code = :code"),
            {"code": req.game_code},
        ).first()
        if game is None:
            raise HTTPException(status_code=400, detail=f"unknown game_code: {req.game_code}")

        status = conn.execute(
            text("SELECT id FROM lobby_statuses WHERE code = 'waiting'")
        ).first()
        if status is None:
            raise HTTPException(status_code=500, detail="lobby_statuses seed missing")

        new_id = conn.execute(
            text("""
                INSERT INTO lobbies (name, game_id, status_id, config, max_players)
                VALUES (:name, :game_id, :status_id, CAST(:config AS JSONB), :max_players)
                RETURNING id
            """),
            {
                "name": req.name,
                "game_id": game.id,
                "status_id": status.id,
                "config": json.dumps(req.config),
                "max_players": req.max_players,
            },
        ).scalar_one()
        return {"id": new_id}


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
