"""FastAPI authentication and authorisation dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.database import get_db
from app.models.user import User

from typing import Optional

_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or missing authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to perform this action",
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Verify token, load user from DB. Raises 401 on any failure."""
    if not credentials:
        raise _UNAUTHORIZED
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _UNAUTHORIZED
    except JWTError:
        raise _UNAUTHORIZED

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise _UNAUTHORIZED
    return user


def require_editor(current_user: User = Depends(get_current_user)) -> User:
    """Allow editor OR admin (editor is the minimum privilege level)."""
    if current_user.role not in ("editor", "admin"):
        raise _FORBIDDEN
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow admin only. Raises 403 for editors."""
    if current_user.role != "admin":
        raise _FORBIDDEN
    return current_user
