"""Catalogue publish + viewer read router."""
from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.user import User
from app.models.publish_run import PublishRun
from app.services.publisher import publish_catalog
from app.storage.base import StorageBackend
from app.storage.local import LocalDiskStorage
from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["catalog"])

# Provide the storage backend as a dependency (you can mock it in tests if you want)
def get_storage() -> StorageBackend:
    return LocalDiskStorage(root=settings.STORAGE_ROOT, base_url=settings.STORAGE_BASE_URL)

@router.post("/admin/catalog/publish", summary="Trigger a catalogue publish run", status_code=202)
def trigger_publish_catalog(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    """
    Builds and atomically writes the published catalogue.
    Admin-only.
    """
    run = publish_catalog(db, storage, str(current_user.id))
    if run.status == "failed":
        raise HTTPException(status_code=400, detail=f"Publish blocked: {run.error_message}")
    return {"run_id": str(run.id), "status": run.status}


@router.get("/admin/publish-runs", summary="Publish run history")
def list_publish_runs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    runs = db.query(PublishRun).order_by(PublishRun.started_at.desc()).all()
    return {"runs": [{"id": str(r.id), "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at, "error_message": r.error_message} for r in runs]}


def _read_current_catalog(storage: StorageBackend) -> dict:
    try:
        pointer_data = storage.get("catalogues/current.json")
        pointer = json.loads(pointer_data)
        catalog_key = pointer.get("current")
        if not catalog_key:
            return {"sections": []}
        catalog_data = storage.get(catalog_key)
        return json.loads(catalog_data)
    except FileNotFoundError:
        return {"sections": []}


@router.get("/catalog", summary="Published catalogue (viewer)")
def get_catalog(storage: StorageBackend = Depends(get_storage)) -> dict:
    return _read_current_catalog(storage)


@router.get("/catalog/search", summary="Search the published catalogue")
def search_catalog(
    q: str | None = None,
    category: str | None = None,
    language: str | None = None,
    section: str | None = None,
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    catalog = _read_current_catalog(storage)
    results = []

    for sec in catalog.get("sections", []):
        if section and sec["id"] != section:
            continue
            
        for show in sec.get("shows", []):
            if category and category not in show.get("categories", []):
                continue
                
            if q and q.lower() not in show["title"].lower():
                continue
                
            # If filtering by language, check if the show has any episodes in this language
            if language:
                has_language = False
                for s in show.get("seasons", []):
                    for ep in s.get("episodes", []):
                        if language in ep.get("languages", {}):
                            has_language = True
                            break
                    if has_language:
                        break
                if not has_language:
                    continue

            results.append(show)

    return {"results": results}
