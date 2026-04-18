import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.avatars import AVATAR_CODES
from src.auth.dependencies import current_user_id
from src.auth.jwt_service import create_token
from src.auth.models import User
from src.auth.password import hash_password, verify_password
from src.auth.schemas import LoginRequest, RegisterRequest
from src.core.db import get_session
from src.core.exceptions import BadRequest, Conflict, NotFound, Unauthorized

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "login": user.login,
        "avatar": user.avatar,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/register", status_code=201)
def register(req: RegisterRequest, session: Session = Depends(get_session)):
    if req.avatar not in AVATAR_CODES:
        raise BadRequest(f"unknown avatar: {req.avatar}")

    existing = session.scalar(select(User).where(User.login == req.login))
    if existing is not None:
        raise Conflict("login already taken")

    user = User(
        login=req.login,
        password_hash=hash_password(req.password),
        avatar=req.avatar,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info("user registered id=%s login=%s", user.id, user.login)
    return {"token": create_token(user.id), "user": _serialize_user(user)}


@router.post("/login")
def login(req: LoginRequest, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.login == req.login))
    if user is None or not verify_password(req.password, user.password_hash):
        raise Unauthorized("invalid credentials")
    logger.info("user login id=%s login=%s", user.id, user.login)
    return {"token": create_token(user.id), "user": _serialize_user(user)}


@router.get("/me")
def me(
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise NotFound("user not found")
    return _serialize_user(user)
