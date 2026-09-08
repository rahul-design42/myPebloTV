"""PublishRun model."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDPrimaryKey


class PublishRun(Base, UUIDPrimaryKey):
    """
    Records each attempt to publish the catalogue.

    Atomicity guarantee: catalogue_key is only set (and status → 'succeeded')
    after the catalogue file is written AND the current-catalogue pointer is
    updated atomically. A failed run leaves the pointer untouched.
    """

    __tablename__ = "publish_runs"

    triggered_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    # running | succeeded | failed
    status = Column(String(20), nullable=False, default="running", index=True)
    catalogue_key = Column(String(1000), nullable=True)
    show_count = Column(Integer, nullable=True)
    episode_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    triggered_by_user = relationship("User", foreign_keys=[triggered_by])

    def __repr__(self) -> str:
        return f"<PublishRun id={self.id} status={self.status}>"
