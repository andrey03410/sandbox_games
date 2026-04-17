from pydantic import BaseModel


class MoveRequest(BaseModel):
    row: int
    col: int
