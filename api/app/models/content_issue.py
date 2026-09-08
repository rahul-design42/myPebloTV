"""ContentIssue model — stores data-quality problems found during seeding or validation."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, UUIDPrimaryKey


class ContentIssue(Base, UUIDPrimaryKey):
    """
    Records data-quality problems that prevent a row from being inserted or published.

    source_episode_id is the raw ID string from the seed data (e.g. "ep_9001").
    It is NOT a foreign key to the episodes table because deliberately invalid
    rows such as ep_9001 are never inserted into episodes; storing an FK would
    make it impossible to record them.

    issue_type examples:
      duplicate_content_group_language
      missing_section
      missing_artwork
      missing_duration
      inconsistent_title_casing
      other

    severity:
      blocking  — prevents publish
      warning   — surfaced in report but does not block publish

    resolved_at: set when a content editor resolves the issue (optional workflow).
    """

    __tablename__ = "content_issues"

    # Raw string ID from source data — intentionally NOT a FK
    source_episode_id = Column(String(100), nullable=True)
    issue_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False)   # blocking | warning
    message = Column(Text, nullable=False)
    raw_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ContentIssue type={self.issue_type} src={self.source_episode_id}>"
