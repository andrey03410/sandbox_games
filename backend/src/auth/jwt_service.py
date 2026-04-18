from datetime import datetime, timedelta, timezone

import jwt

from src.core.exceptions import Unauthorized
from src.core.settings import settings


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_ttl_hours)
    return jwt.encode(
        {"sub": str(user_id), "exp": exp},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("token expired")
    except jwt.PyJWTError:
        raise Unauthorized("invalid token")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise Unauthorized("malformed token payload")
