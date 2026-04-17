from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from src.core.config import JWT_ALGORITHM, JWT_SECRET, JWT_TTL_HOURS


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="malformed token payload")
