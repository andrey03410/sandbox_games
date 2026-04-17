from pydantic import BaseModel


class JoinRequest(BaseModel):
    role: str
