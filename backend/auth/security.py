"""Password hashing (bcrypt directly -- passlib's CryptContext wrapper
doesn't recognize bcrypt>=4.1's version API and fails its own self-test) and
login-token issuance/verification (PyJWT). Stateless: the token carries the
identity fields the frontend and lifecycle endpoints need, so verifying a
request never round-trips to Mongo.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

TOKEN_TTL_HOURS = 12
JWT_ALGORITHM = "HS256"


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set (check .env)")
    return secret


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(claims: dict) -> str:
    payload = {
        **claims,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (expired, malformed, bad signature) on failure --
    callers turn that into a 401, never a 500."""
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
