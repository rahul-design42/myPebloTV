"""JWT creation and verification."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

ALGORITHM = settings.ALGORITHM


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token.

    The payload must include at minimum:
      sub  — user ID (UUID string)
      role — user role string

    Expiry is set from ACCESS_TOKEN_EXPIRE_MINUTES setting.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Raises jose.JWTError on invalid/expired tokens.
    The caller is responsible for converting JWTError into HTTP 401.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def extract_role(token: str) -> str | None:
    """Extract the role claim from a token without raising on error."""
    try:
        payload = decode_access_token(token)
        return payload.get("role")
    except JWTError:
        return None
