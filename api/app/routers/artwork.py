"""Artwork upload/delete router."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_editor
from app.database import get_db
from app.models import Artwork, Show, Episode
from app.models.user import User
from app.services.artwork_validator import validate_artwork
from app.storage.base import StorageBackend
from app.storage.local import LocalDiskStorage
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin-artwork"])

def get_storage() -> StorageBackend:
    return LocalDiskStorage(root=settings.STORAGE_ROOT, base_url=settings.STORAGE_BASE_URL)


@router.post("/artwork", summary="Upload artwork", status_code=201)
def upload_artwork(
    kind: str = Form(...),
    show_id: Optional[str] = Form(None),
    episode_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    if kind not in ("poster", "banner", "thumbnail"):
        raise HTTPException(status_code=400, detail="Invalid artwork kind")
    
    if kind in ("poster", "banner") and not show_id:
        raise HTTPException(status_code=400, detail=f"show_id is required for {kind}")
    if kind == "thumbnail" and not episode_id:
        raise HTTPException(status_code=400, detail="episode_id is required for thumbnail")

    # Read and validate image
    data = file.file.read()
    result = validate_artwork(kind, data)
    
    if not result.valid:
        raise HTTPException(status_code=400, detail={"errors": result.errors})

    # Validate parent entity exists
    if show_id:
        show = db.query(Show).filter(Show.id == show_id).first()
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        
        # Check if artwork of this kind already exists for the show
        existing = db.query(Artwork).filter(Artwork.show_id == show_id, Artwork.kind == kind).first()
        if existing:
            # We could delete the old one, but for simplicity let's just return error or overwrite
            db.delete(existing)

    if episode_id:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
            
        existing = db.query(Artwork).filter(Artwork.episode_id == episode_id, Artwork.kind == kind).first()
        if existing:
            db.delete(existing)

    import hashlib
    checksum = hashlib.sha256(data).hexdigest()
    
    # Generate storage key based on validated format
    fmt = result.format.lower()
    ext = f".{fmt}" if fmt in ("png", "webp", "gif") else ".jpg"

    if show_id:
        storage_key = f"shows/{show_id}/{kind}_{uuid.uuid4().hex[:8]}{ext}"
    else:
        storage_key = f"episodes/{episode_id}/{kind}_{uuid.uuid4().hex[:8]}{ext}"

    # Determine safe content type based on extension
    content_types = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".jpg": "image/jpeg"
    }
    safe_content_type = content_types.get(ext, "image/jpeg")

    storage.put(storage_key, data, content_type=safe_content_type)

    artwork = Artwork(
        show_id=show_id,
        episode_id=episode_id,
        kind=kind,
        storage_key=storage_key,
        width=result.width,
        height=result.height,
        size_bytes=result.size_bytes,
        checksum=checksum,
    )
    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    return {
        "id": str(artwork.id),
        "url": storage.url_for(storage_key),
        "kind": artwork.kind,
    }


@router.delete("/artwork/{artwork_id}", summary="Delete artwork", status_code=204)
def delete_artwork(
    artwork_id: str, 
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> Response:
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
        
    db.delete(artwork)
    db.commit()
    return Response(status_code=204)
