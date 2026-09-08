"""User model."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, String

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    # Allowed values: editor | admin  (enforced by DB CHECK in migration)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<User email={self.email} role={self.role}>"
