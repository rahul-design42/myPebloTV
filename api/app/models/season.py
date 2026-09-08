"""Season model."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDPrimaryKey


class Season(Base, UUIDPrimaryKey):
    """
    A season belonging to a show.

    season_number 0 is reserved for trailers (per reference.json convention).
    Season 0 must never appear as a normal viewer season; enforced at the
    publisher/catalogue layer, not here.

    UNIQUE(show_id, season_number) enforced in DB.
    """

    __tablename__ = "seasons"

    show_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_number = Column(Integer, nullable=False)

    show = relationship("Show", back_populates="seasons")
    episodes = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="Episode.episode_number",
    )

    __table_args__ = (
        UniqueConstraint("show_id", "season_number", name="uq_season_show_number"),
    )

    def __repr__(self) -> str:
        return f"<Season show_id={self.show_id} season_number={self.season_number}>"
