"""Initial schema — all tables with constraints and indexes.

Revision ID: 0001
Revises: None
Create Date: 2026-09-07

Tables created:
  users, shows, show_categories, seasons, episodes,
  artwork, publish_runs, content_issues

Key constraints:
  - episodes: UNIQUE(content_group, language)  — never weakened
  - artwork: CHECK enforces kind↔ownership mapping
  - seasons: UNIQUE(show_id, season_number)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('editor', 'admin')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ------------------------------------------------------------------ shows
    op.create_table(
        "shows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("section", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shows"),
        sa.UniqueConstraint("slug", name="uq_shows_slug"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')", name="ck_shows_status"
        ),
    )
    op.create_index("ix_shows_slug", "shows", ["slug"])
    op.create_index("ix_shows_status", "shows", ["status"])
    op.create_index("ix_shows_section", "shows", ["section"])

    # --------------------------------------------------------- show_categories
    op.create_table(
        "show_categories",
        sa.Column("show_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(
            ["show_id"], ["shows.id"], name="fk_show_categories_show", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("show_id", "category", name="pk_show_categories"),
    )

    # ---------------------------------------------------------------- seasons
    op.create_table(
        "seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("show_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["show_id"], ["shows.id"], name="fk_seasons_show", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_seasons"),
        sa.UniqueConstraint("show_id", "season_number", name="uq_season_show_number"),
    )
    op.create_index("ix_seasons_show_id", "seasons", ["show_id"])

    # --------------------------------------------------------------- episodes
    op.create_table(
        "episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_group", sa.String(500), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["season_id"], ["seasons.id"], name="fk_episodes_season", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_episodes"),
        # THE critical constraint — must not be weakened to accommodate bad seed data
        sa.UniqueConstraint(
            "content_group", "language", name="uq_episode_content_group_language"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')", name="ck_episodes_status"
        ),
        sa.CheckConstraint(
            "language IN ('en', 'hi')", name="ck_episodes_language"
        ),
    )
    op.create_index("ix_episodes_season_id", "episodes", ["season_id"])
    op.create_index("ix_episodes_content_group", "episodes", ["content_group"])
    op.create_index("ix_episodes_status", "episodes", ["status"])

    # ---------------------------------------------------------------- artwork
    op.create_table(
        "artwork",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("show_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["show_id"], ["shows.id"], name="fk_artwork_show", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"], ["episodes.id"], name="fk_artwork_episode", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artwork"),
        sa.CheckConstraint("kind IN ('poster', 'banner', 'thumbnail')", name="ck_artwork_kind"),
        # Enforces: poster/banner → show only; thumbnail → episode only
        sa.CheckConstraint(
            "(kind IN ('poster', 'banner') AND show_id IS NOT NULL AND episode_id IS NULL) "
            "OR (kind = 'thumbnail' AND episode_id IS NOT NULL AND show_id IS NULL)",
            name="ck_artwork_ownership",
        ),
    )
    op.create_index("ix_artwork_show_id", "artwork", ["show_id"])
    op.create_index("ix_artwork_episode_id", "artwork", ["episode_id"])

    # ---------------------------------------------------------- publish_runs
    op.create_table(
        "publish_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("catalogue_key", sa.String(1000), nullable=True),
        sa.Column("show_count", sa.Integer(), nullable=True),
        sa.Column("episode_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["triggered_by"], ["users.id"], name="fk_publish_runs_user"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publish_runs"),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_publish_runs_status"
        ),
    )
    op.create_index("ix_publish_runs_status", "publish_runs", ["status"])

    # ------------------------------------------------------- content_issues
    op.create_table(
        "content_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Plain string — intentionally NOT a FK (invalid rows are never in episodes)
        sa.Column("source_episode_id", sa.String(100), nullable=True),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_content_issues"),
        sa.CheckConstraint(
            "severity IN ('blocking', 'warning')", name="ck_content_issues_severity"
        ),
    )
    op.create_index("ix_content_issues_issue_type", "content_issues", ["issue_type"])
    op.create_index("ix_content_issues_source_episode_id", "content_issues", ["source_episode_id"])


def downgrade() -> None:
    op.drop_table("content_issues")
    op.drop_table("publish_runs")
    op.drop_table("artwork")
    op.drop_table("episodes")
    op.drop_table("seasons")
    op.drop_table("show_categories")
    op.drop_table("shows")
    op.drop_table("users")
