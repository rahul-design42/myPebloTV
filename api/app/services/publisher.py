"""Publisher service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Show, Season, Episode, PublishRun
from app.storage.base import StorageBackend

settings = get_settings()


def publish_catalog(db: Session, storage: StorageBackend, user_id: str) -> PublishRun:
    """
    Builds the catalogue from the DB and writes it atomically to storage.
    """
    run_id = str(uuid.uuid4())
    run = PublishRun(
        id=run_id,
        triggered_by=user_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()

    try:
        from app.services.validator import get_validation_report
        report = get_validation_report(db)
        blocking = report.get("blocking", {})
        has_blockers = any(len(issues) > 0 for issues in blocking.values())
        
        if has_blockers:
            raise ValueError(json.dumps(blocking))

        reference = settings.reference_data()
        sections_order = reference.get("sections", [])

        published_shows = (
            db.query(Show)
            .filter(Show.status == "published")
            .order_by(Show.title.asc())
            .all()
        )

        catalog_sections = {section: [] for section in sections_order}
        catalog_sections["unsectioned"] = [] # In case any show has section not in order

        show_count = 0
        episode_count = 0

        for show in published_shows:
            show_dict = {
                "id": str(show.id),
                "title": show.title,
                "slug": show.slug,
                "synopsis": show.synopsis,
                "categories": [c.category for c in show.categories],
                "artwork": {a.kind: storage.url_for(a.storage_key) for a in show.artwork},
                "seasons": [],
            }

            for season in show.seasons:

                # Group episodes by content_group
                content_groups = {}
                for ep in season.episodes:
                    if ep.status != "published":
                        continue

                    if ep.content_group not in content_groups:
                        content_groups[ep.content_group] = {
                            "content_group": ep.content_group,
                            "episode_number": ep.episode_number,
                            "title": ep.title,
                            "duration_seconds": ep.duration_seconds,
                            "languages": {},
                        }
                    
                    content_groups[ep.content_group]["languages"][ep.language] = {
                        "id": str(ep.id),
                        "artwork": {a.kind: storage.url_for(a.storage_key) for a in ep.artwork},
                    }
                    episode_count += 1

                if content_groups:
                    # Sort grouped episodes by episode_number
                    sorted_episodes = sorted(
                        content_groups.values(), key=lambda x: x["episode_number"]
                    )
                    show_dict["seasons"].append({
                        "id": str(season.id),
                        "season_number": season.season_number,
                        "episodes": sorted_episodes,
                    })

            if show_dict["seasons"]:
                show_count += 1
                sec = show.section
                if sec in catalog_sections:
                    catalog_sections[sec].append(show_dict)
                else:
                    catalog_sections["unsectioned"].append(show_dict)

        # Build final catalog matching reference section order
        final_catalog = {
            "version": "1.0",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "sections": [],
        }

        for sec in sections_order:
            if catalog_sections[sec]:
                final_catalog["sections"].append({
                    "id": sec,
                    "shows": catalog_sections[sec],
                })
        
        if catalog_sections["unsectioned"]:
            final_catalog["sections"].append({
                "id": "unsectioned",
                "shows": catalog_sections["unsectioned"],
            })

        catalog_json = json.dumps(final_catalog, indent=2).encode("utf-8")
        catalogue_key = f"catalogues/{run_id}.json"

        # 1. Write the new catalogue file
        storage.put(catalogue_key, catalog_json, content_type="application/json")

        # 2. Atomically update the current pointer
        pointer_data = json.dumps({"current": catalogue_key}).encode("utf-8")
        storage.atomic_pointer_write("catalogues/current.json", pointer_data)

        run.status = "succeeded"
        run.catalogue_key = catalogue_key
        run.show_count = show_count
        run.episode_count = episode_count

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

    return run
