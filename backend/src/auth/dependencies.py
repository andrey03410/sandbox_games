from fastapi import Header

from src.auth.jwt_service import decode_token
from src.core.exceptions import Unauthorized


def current_user_id(authorization: str | None = Header(default=None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise Unauthorized("missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_token(token)
