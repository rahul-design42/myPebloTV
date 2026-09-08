"""Show model."""
from __future__ import annotations

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Show(Base, UUIDPrimaryKey, TimestampMixin):
    """
    A TV show.

    Status values: draft | published | archived
    Section is nullable — shows under development may not have a section yet.
    A published show MUST have a non-null section; enforced at application layer
    (not DB CHECK) so the validation report can surface it gracefully.

    Valid sections come from reference.json: featured, series, minisodes, songs.
    """

    __tablename__ = "shows"

    title = Column(String(500), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    synopsis = Column(Text, nullable=True)
    section = Column(String(50), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)

    # Relationships
    categories = relationship(
        "ShowCategory", back_populates="show", cascade="all, delete-orphan"
    )
    seasons = relationship(
        "Season", back_populates="show", cascade="all, delete-orphan", order_by="Season.season_number"
    )
    artwork = relationship(
        "Artwork",
        primaryjoin="and_(Artwork.show_id == Show.id, Artwork.show_id.isnot(None))",
        cascade="all, delete-orphan",
        foreign_keys="Artwork.show_id",
    )

    def __repr__(self) -> str:
        return f"<Show slug={self.slug} status={self.status}>"
