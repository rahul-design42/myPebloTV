"""Application configuration loaded from environment variables."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://peblo:peblo@localhost:5432/peblodb"

    # JWT
    SECRET_KEY: str = "7f3a91c8e2b64d10a5c9f7138d42be67"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Storage
    STORAGE_ROOT: str = "./storage"
    STORAGE_BASE_URL: str = "http://localhost:8000/media"

    # Seed / reference paths (overridden in Docker via env)
    REFERENCE_JSON_PATH: str = "/seed/reference.json"
    SEED_DATA_PATH: str = "/seed/seed_shows.json"
    SEED_ASSETS_DIR: str = "/seed/assets"

    def reference_data(self) -> dict:
        """Load reference.json, trying configured path then local fallback."""
        for candidate in [
            Path(self.REFERENCE_JSON_PATH),
            Path(__file__).parent.parent.parent / "seed" / "reference.json",
        ]:
            if candidate.exists():
                return json.loads(candidate.read_text())
        return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
    