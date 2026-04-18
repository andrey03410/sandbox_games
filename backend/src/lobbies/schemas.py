from pydantic import BaseModel, Field


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
