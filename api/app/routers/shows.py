"""Shows CRUD router."""
from __future__ import annotations

from typing import List, Optional, Literal
import math

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from pydantic import BaseModel

from app.auth.dependencies import require_editor
from app.database import get_db
from app.models.user import User
from app.models import Show, Season, Episode, ShowCategory, Artwork

router = APIRouter(prefix="/admin", tags=["admin-shows"])

# --- Schemas ---

class ShowCreate(BaseModel):
    title: str
    slug: str
    synopsis: Optional[str] = None
    section: Optional[str] = None
    status: str = "draft"
    categories: List[str] = []

class ShowUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    synopsis: Optional[str] = None
    section: Optional[str] = None
    status: Optional[str] = None
    categories: Optional[List[str]] = None

class SeasonCreate(BaseModel):
    season_number: int

class SeasonUpdate(BaseModel):
    season_number: Optional[int] = None

class EpisodeCreate(BaseModel):
    content_group: str
    language: Literal["en", "hi"]
    title: str
    episode_number: int
    duration_seconds: Optional[int] = None
    status: str = "draft"

class EpisodeUpdate(BaseModel):
    content_group: Optional[str] = None
    language: Optional[Literal["en", "hi"]] = None
    title: Optional[str] = None
    episode_number: Optional[int] = None
    duration_seconds: Optional[int] = None
    status: Optional[str] = None


# --- Shows ---

@router.get("/shows", summary="List shows")
def list_shows(
    q: Optional[str] = Query(None, description="Search term for show title"),
    section: Optional[str] = Query(None, description="Filter by section"),
    status: Optional[str] = Query(None, description="Filter by status"),
    language: Optional[str] = Query(None, description="Filter by episode language availability"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Show)

    if q:
        query = query.filter(Show.title.ilike(f"%{q}%"))
    if section:
        query = query.filter(Show.section == section)
    if status:
        query = query.filter(Show.status == status)
    
    if language:
        # Show has at least one episode with this language
        query = query.join(Season, Show.id == Season.show_id).join(Episode, Season.id == Episode.season_id).filter(Episode.language == language)

    # Count total before pagination
    total_items = query.count()
    total_pages = math.ceil(total_items / page_size)

    shows = query.order_by(Show.title.asc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for s in shows:
        items.append({
            "id": str(s.id),
            "title": s.title,
            "slug": s.slug,
            "section": s.section,
            "status": s.status,
            "categories": [c.category for c in s.categories],
        })

    return {
        "items": items,
        "total_items": total_items,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size
    }


@router.get("/shows/{show_id}", summary="Get show details")
def get_show(
    show_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    artworks = []
    for a in show.artwork:
        artworks.append({
            "id": str(a.id),
            "kind": a.kind,
            "storage_key": a.storage_key,
        })
        
    return {
        "id": str(show.id),
        "title": show.title,
        "slug": show.slug,
        "synopsis": show.synopsis,
        "section": show.section,
        "status": show.status,
        "categories": [c.category for c in show.categories],
        "created_at": show.created_at,
        "updated_at": show.updated_at,
        "artwork": artworks
    }


@router.post("/shows", summary="Create show", status_code=201)
def create_show(
    data: ShowCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    if db.query(Show).filter(Show.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
        
    show = Show(
        title=data.title,
        slug=data.slug,
        synopsis=data.synopsis,
        section=data.section,
        status=data.status,
    )
    db.add(show)
    db.flush()
    
    for cat in data.categories:
        db.add(ShowCategory(show_id=show.id, category=cat))
        
    db.commit()
    return {"id": str(show.id), "slug": show.slug}


@router.put("/shows/{show_id}", summary="Update show")
def update_show(
    show_id: str,
    data: ShowUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    if data.slug is not None and data.slug != show.slug:
        if db.query(Show).filter(Show.slug == data.slug).first():
            raise HTTPException(status_code=400, detail="Slug already exists")
        show.slug = data.slug

    if data.title is not None: show.title = data.title
    if data.synopsis is not None: show.synopsis = data.synopsis
    if data.section is not None: show.section = data.section
    if data.status is not None: show.status = data.status
    
    if data.categories is not None:
        db.query(ShowCategory).filter(ShowCategory.show_id == show.id).delete()
        for cat in data.categories:
            db.add(ShowCategory(show_id=show.id, category=cat))
            
    db.commit()
    return {"id": str(show.id), "slug": show.slug}


@router.delete("/shows/{show_id}", summary="Delete show", status_code=204)
def delete_show(
    show_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> Response:
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    # Check if there are seasons
    if db.query(Season).filter(Season.show_id == show_id).first():
        raise HTTPException(status_code=400, detail="Cannot delete show with existing seasons. Delete seasons first.")
        
    # Delete artworks
    db.query(Artwork).filter(Artwork.show_id == show_id).delete()
    db.delete(show)
    db.commit()
    return Response(status_code=204)


# --- Seasons ---

@router.get("/shows/{show_id}/seasons", summary="List seasons for a show")
def list_seasons(
    show_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    seasons = db.query(Season).filter(Season.show_id == show_id).order_by(Season.season_number.asc()).all()
    
    return {"seasons": [{"id": str(s.id), "season_number": s.season_number} for s in seasons]}


@router.post("/shows/{show_id}/seasons", summary="Create a season", status_code=201)
def create_season(
    show_id: str,
    data: SeasonCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    if db.query(Season).filter(Season.show_id == show_id, Season.season_number == data.season_number).first():
        raise HTTPException(status_code=400, detail="Season number already exists for this show")
        
    season = Season(show_id=show_id, season_number=data.season_number)
    db.add(season)
    db.commit()
    db.refresh(season)
    
    return {"id": str(season.id), "season_number": season.season_number}


@router.put("/seasons/{season_id}", summary="Update a season")
def update_season(
    season_id: str,
    data: SeasonUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
        
    if data.season_number is not None and data.season_number != season.season_number:
        if db.query(Season).filter(Season.show_id == season.show_id, Season.season_number == data.season_number).first():
            raise HTTPException(status_code=400, detail="Season number already exists for this show")
        season.season_number = data.season_number
        
    db.commit()
    return {"id": str(season.id), "season_number": season.season_number}


@router.delete("/seasons/{season_id}", summary="Delete a season", status_code=204)
def delete_season(
    season_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> Response:
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
        
    if db.query(Episode).filter(Episode.season_id == season_id).first():
        raise HTTPException(status_code=400, detail="Cannot delete season with existing episodes. Delete episodes first.")
        
    db.delete(season)
    db.commit()
    return Response(status_code=204)


# --- Episodes ---

@router.get("/seasons/{season_id}/episodes", summary="List episodes for a season")
def list_episodes(
    season_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
        
    episodes = db.query(Episode).filter(Episode.season_id == season_id).order_by(Episode.episode_number.asc()).all()
    
    items = []
    for e in episodes:
        artworks = [{"id": str(a.id), "kind": a.kind, "storage_key": a.storage_key} for a in e.artwork]
        items.append({
            "id": str(e.id),
            "content_group": e.content_group,
            "language": e.language,
            "title": e.title,
            "episode_number": e.episode_number,
            "duration_seconds": e.duration_seconds,
            "status": e.status,
            "artwork": artworks
        })
        
    return {"episodes": items}


@router.post("/seasons/{season_id}/episodes", summary="Create an episode", status_code=201)
def create_episode(
    season_id: str,
    data: EpisodeCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
        
    # Check UNIQUE(content_group, language)
    if db.query(Episode).filter(Episode.content_group == data.content_group, Episode.language == data.language).first():
        raise HTTPException(status_code=400, detail="Episode with this content group and language already exists")
        
    episode = Episode(
        season_id=season_id,
        content_group=data.content_group,
        language=data.language,
        title=data.title,
        episode_number=data.episode_number,
        duration_seconds=data.duration_seconds,
        status=data.status
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    
    return {"id": str(episode.id)}


@router.put("/episodes/{episode_id}", summary="Update an episode")
def update_episode(
    episode_id: str,
    data: EpisodeUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> dict:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
        
    # Check UNIQUE(content_group, language) if modifying either
    new_cg = data.content_group if data.content_group is not None else episode.content_group
    new_lang = data.language if data.language is not None else episode.language
    
    if (new_cg != episode.content_group or new_lang != episode.language):
        if db.query(Episode).filter(Episode.content_group == new_cg, Episode.language == new_lang).first():
            raise HTTPException(status_code=400, detail="Episode with this content group and language already exists")
            
    if data.content_group is not None: episode.content_group = data.content_group
    if data.language is not None: episode.language = data.language
    if data.title is not None: episode.title = data.title
    if data.episode_number is not None: episode.episode_number = data.episode_number
    if data.duration_seconds is not None: episode.duration_seconds = data.duration_seconds
    if data.status is not None: episode.status = data.status
    
    db.commit()
    return {"id": str(episode.id)}


@router.delete("/episodes/{episode_id}", summary="Delete an episode", status_code=204)
def delete_episode(
    episode_id: str,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
) -> Response:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
        
    # Delete associated artwork
    db.query(Artwork).filter(Artwork.episode_id == episode_id).delete()
    
    db.delete(episode)
    db.commit()
    return Response(status_code=204)
