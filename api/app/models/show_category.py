"""ShowCategory join model."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class ShowCategory(Base):
    """
    Many-to-many between shows and category strings.
    Categories are plain strings validated against reference.json at app layer.
    """

    __tablename__ = "show_categories"

    show_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shows.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    category = Column(String(100), primary_key=True, nullable=False)

    show = relationship("Show", back_populates="categories")

    def __repr__(self) -> str:
        return f"<ShowCategory show_id={self.show_id} category={self.category}>"
