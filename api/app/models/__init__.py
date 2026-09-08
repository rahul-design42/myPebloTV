"""Import all models so SQLAlchemy metadata is fully populated for migrations."""
from app.models.base import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.show import Show  # noqa: F401
from app.models.show_category import ShowCategory  # noqa: F401
from app.models.season import Season  # noqa: F401
from app.models.episode import Episode  # noqa: F401
from app.models.artwork import Artwork  # noqa: F401
from app.models.publish_run import PublishRun  # noqa: F401
from app.models.content_issue import ContentIssue  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Show",
    "ShowCategory",
    "Season",
    "Episode",
    "Artwork",
    "PublishRun",
    "ContentIssue",
]
