"""FastAPI dependency that turns an Authorization: Bearer <token> header into
the caller's identity, for endpoints that need to know -- and record -- who
is actually acting (the lifecycle actions: acknowledge/escalate/resolve)."""
import jwt
from fastapi import Header, HTTPException

from .security import decode_access_token


class CurrentUser:
    def __init__(self, claims: dict):
        self.username: str = claims["sub"]
        self.display_name: str = claims["display_name"]
        self.role: str = claims["role"]
        self.agent_id: str | None = claims.get("agent_id")
        self.area: str | None = claims.get("area")
        self.provider: str | None = claims.get("provider")


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid token: {e}") from e
    return CurrentUser(claims)
