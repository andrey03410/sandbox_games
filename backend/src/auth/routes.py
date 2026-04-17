from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from src.auth.avatars import AVATAR_CODES
from src.auth.dependencies import current_user_id
from src.auth.jwt_service import create_token
from src.auth.password import hash_password, verify_password
from src.auth.schemas.login_request import LoginRequest
from src.auth.schemas.register_request import RegisterRequest
from src.core.db import engine

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _serialize_user(row) -> dict:
    return {
        "id": row.id,
        "login": row.login,
        "avatar": row.avatar,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/register", status_code=201)
def register(req: RegisterRequest):
    if req.avatar not in AVATAR_CODES:
        raise HTTPException(status_code=400, detail=f"unknown avatar: {req.avatar}")
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE login = :login"),
            {"login": req.login},
        ).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="login already taken")
        row = conn.execute(
            text("""
                INSERT INTO users (login, password_hash, avatar)
                VALUES (:login, :hash, :avatar)
                RETURNING id, login, avatar, created_at
            """),
            {
                "login": req.login,
                "hash": hash_password(req.password),
                "avatar": req.avatar,
            },
        ).first()
    return {"token": create_token(row.id), "user": _serialize_user(row)}


@router.post("/login")
def login(req: LoginRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, login, password_hash, avatar, created_at
                FROM users WHERE login = :login
            """),
            {"login": req.login},
        ).first()
    if row is None or not verify_password(req.password, row.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_token(row.id), "user": _serialize_user(row)}


@router.get("/me")
def me(user_id: int = Depends(current_user_id)):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, login, avatar, created_at FROM users WHERE id = :id"),
            {"id": user_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _serialize_user(row)
