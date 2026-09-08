"""Validation report service."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Artwork, ContentIssue, Episode, Season, Show

settings = get_settings()


def get_validation_report(db: Session) -> dict:
    """
    Generate the validation report.
    Returns a dict with blocking issues and non-blocking warnings.
    """
    report: dict = {
        "blocking": {
            "missing_artwork": [],
            "missing_duration": [],
            "shows_without_section": [],
            "duplicate_content_group_language": [],
        },
        "warnings": [],
    }

    # Load reference.json to check sections
    reference = settings.reference_data()
    valid_sections = reference.get("sections", [])

    # --- 1. Shows without valid sections (blocking if show is published) ---
    published_shows = db.query(Show).filter(Show.status == "published").all()
    for show in published_shows:
        if show.section is None or show.section not in valid_sections:
            report["blocking"]["shows_without_section"].append({
                "show_id": str(show.id),
                "slug": show.slug,
                "title": show.title,
                "section": show.section,
            })

    # --- 2. Missing artwork ---
    # Shows (poster, banner)
    for show in published_shows:
        show_art = {a.kind for a in show.artwork}
        missing = []
        if "poster" not in show_art:
            missing.append("poster")
        if "banner" not in show_art:
            missing.append("banner")
        if missing:
            report["blocking"]["missing_artwork"].append({
                "level": "show",
                "show_id": str(show.id),
                "slug": show.slug,
                "missing": missing,
            })

    # Episodes (thumbnail)
    published_episodes = db.query(Episode).filter(Episode.status == "published").all()
    for ep in published_episodes:
        ep_art = {a.kind for a in ep.artwork}
        if "thumbnail" not in ep_art:
            report["blocking"]["missing_artwork"].append({
                "level": "episode",
                "episode_id": str(ep.id),
                "content_group": ep.content_group,
                "language": ep.language,
                "missing": ["thumbnail"],
            })

    # --- 3. Missing duration ---
    for ep in published_episodes:
        if ep.duration_seconds is None or ep.duration_seconds <= 0:
            report["blocking"]["missing_duration"].append({
                "episode_id": str(ep.id),
                "content_group": ep.content_group,
                "language": ep.language,
                "duration_seconds": ep.duration_seconds,
            })

    # --- 4. Duplicate content_group/language ---
    # Read from content_issues table
    duplicates = (
        db.query(ContentIssue)
        .filter(ContentIssue.issue_type == "duplicate_content_group_language")
        .all()
    )
    for dup in duplicates:
        report["blocking"]["duplicate_content_group_language"].append({
            "issue_id": str(dup.id),
            "source_episode_id": dup.source_episode_id,
            "message": dup.message,
        })

    # --- Warnings ---
    # Example warning: casing inconsistencies (can be added here)

    return report
