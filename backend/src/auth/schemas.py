from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=200)
    avatar: str = "nebula"
