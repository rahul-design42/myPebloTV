"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, artwork, catalog, health, shows, validation

settings = get_settings()

app = FastAPI(
    title="Peblo TV Mini API",
    description=(
        "Internal CMS + published catalogue API for Peblo TV Mini. "
        "Roles: editor (CRUD) | admin (CRUD + publish + validation report)."
    ),
    version="1.0.0",
)

from fastapi.staticfiles import StaticFiles

# CORS — tighten origins in production via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media storage statically
import os
os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.STORAGE_ROOT), name="media")

# Mount routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(shows.router)
app.include_router(artwork.router)
app.include_router(validation.router)
app.include_router(catalog.router)
