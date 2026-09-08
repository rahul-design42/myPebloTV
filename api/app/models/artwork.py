"""Artwork model."""
from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Artwork(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Artwork record stored behind the StorageBackend.

    Ownership rules (enforced by DB CHECK constraint):
      poster  → belongs to a show  (show_id NOT NULL, episode_id NULL)
      banner  → belongs to a show  (show_id NOT NULL, episode_id NULL)
      thumbnail → belongs to an episode (episode_id NOT NULL, show_id NULL)

    Exactly one of show_id / episode_id must be populated — the CHECK ensures this.

    storage_key is the backend-relative path; url_for() resolves it to a URL.
    checksum is SHA-256 hex of the raw file bytes.
    """

    __tablename__ = "artwork"

    show_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    episode_id = Column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind = Column(String(20), nullable=False)       # poster | banner | thumbnail
    storage_key = Column(String(1000), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)   # SHA-256 hex

    show = relationship(
        "Show",
        back_populates="artwork",
        foreign_keys=[show_id],
    )
    episode = relationship(
        "Episode",
        back_populates="artwork",
        foreign_keys=[episode_id],
    )

    __table_args__ = (
        CheckConstraint(
            "(kind IN ('poster', 'banner') AND show_id IS NOT NULL AND episode_id IS NULL) "
            "OR (kind = 'thumbnail' AND episode_id IS NOT NULL AND show_id IS NULL)",
            name="ck_artwork_ownership",
        ),
    )

    def __repr__(self) -> str:
        return f"<Artwork kind={self.kind} key={self.storage_key}>"
