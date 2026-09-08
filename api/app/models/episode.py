"""Episode model."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Episode(Base, UUIDPrimaryKey, TimestampMixin):
    """
    A single language variant of an episode.

    content_group identifies which episodes are language variants of the same
    episode (per reference.json convention). UNIQUE(content_group, language)
    is enforced at the database level and must NOT be weakened.

    The seed loader handles the deliberate duplicate row (ep_9001) in Python
    before attempting insertion — storing it in content_issues instead.

    Valid languages: en | hi (from reference.json, enforced at app layer).
    """

    __tablename__ = "episodes"

    season_id = Column(
        UUID(as_uuid=True),
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_group = Column(String(500), nullable=False, index=True)
    language = Column(String(10), nullable=False)
    title = Column(String(500), nullable=False)
    episode_number = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)

    season = relationship("Season", back_populates="episodes")
    artwork = relationship(
        "Artwork",
        primaryjoin="and_(Artwork.episode_id == Episode.id, Artwork.episode_id.isnot(None))",
        cascade="all, delete-orphan",
        foreign_keys="Artwork.episode_id",
    )

    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_episode_content_group_language"),
    )

    def __repr__(self) -> str:
        return f"<Episode content_group={self.content_group} lang={self.language}>"
