"""
Idempotent seed loader for Peblo TV Mini.

Usage (as script):
    python seed/seed_loader.py

Usage (as module — e.g. from tests):
    from seed.seed_loader import run_seed
    run_seed(db_session, storage, assets_dir, seed_data, ref_data)

========================================================================
Show status inference rule (documented explicitly):
  seed_shows.json is episode-flat — there is no explicit show-level status
  field in the seed format.  Status is therefore inferred per-show as:

    "published"  if ANY episode row for that slug has status="published"
    "draft"      if ALL episode rows for that slug have status="draft"

  Rationale: a show is only meaningful in the published catalogue if it has
  at least one publishable episode.  The inference does not hide any
  validation problem because:
    - Rhyme Rangers (all draft) → inferred "draft" → null section is not a
      publish-blocking issue for a draft show, but WILL appear in the
      validation report once someone attempts to publish it.
    - Number Nest (mixed: 6 published + 2 draft) → inferred "published" →
      the two draft episodes simply won't appear in the catalogue.

========================================================================
Artwork seeding rules:
  The seed's artwork_available field is a declaration of intent, NOT proof
  that a file exists.  Two conditions must BOTH be true before an Artwork
  record is created:

    1. The artwork kind appears in the episode row's artwork_available list.
    2. The corresponding "good" asset file actually exists on disk in
       assets_dir.

  Asset mapping (good assets only):
    poster    → poster_good.jpg   (show-level artwork)
    banner    → banner_good.jpg   (show-level artwork)
    thumbnail → thumb_good.jpg    (episode-level artwork)

  Consequence: ep_0036 (Discover India ep 4, artwork_available=[]) gets NO
  thumbnail record and will appear as a blocking validation issue.

  Show-level poster/banner are created once per show (not per episode).
  They are created if ANY episode in the show lists that kind in
  artwork_available AND the asset file exists.

========================================================================
Duplicate handling:
  The DB has UNIQUE(content_group, language) on episodes — this constraint
  must NOT be weakened.  The seed loader detects duplicates in Python BEFORE
  attempting any insert:

    - First occurrence of (content_group, language) → inserted normally.
    - Subsequent occurrences → stored in content_issues with
      issue_type="duplicate_content_group_language", severity="blocking".

  ep_9001 is the deliberate duplicate: content_group=motis-many-lives-s01e02,
  language=hi.  Its inconsistent title ("The Lost Kite (v2)") confirms it
  is the bad row.  ep_0004 (same CG+lang, title "Rain on the Roof") wins.

========================================================================
Idempotency:
  Every insert is guarded by a prior lookup.  Running the seed twice
  produces the same DB state.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Allow running as a script from the repo root or from inside api/
_repo_root = Path(__file__).parent.parent
_api_dir = _repo_root / "api"
for _p in [str(_api_dir), str(_repo_root), "/app"]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.models import (  # noqa: E402
    Artwork,
    ContentIssue,
    Episode,
    Season,
    Show,
    ShowCategory,
    User,
)
from app.storage.local import LocalDiskStorage  # noqa: E402

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Asset → good-file mapping
# ---------------------------------------------------------------------------
_GOOD_ASSET_FILES = {
    "poster": "poster_good.jpg",
    "banner": "banner_good.jpg",
    "thumbnail": "thumb_good.jpg",
}

_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _img_info(path: str) -> tuple[int, int, int, str]:
    """Return (width, height, size_bytes, checksum)."""
    data = Path(path).read_bytes()
    img = Image.open(path)
    w, h = img.size
    return w, h, len(data), _sha256(data)


# ---------------------------------------------------------------------------
# Default users
# ---------------------------------------------------------------------------
_DEFAULT_USERS = [
    {"email": "admin@peblo.tv", "password": "admin123", "role": "admin"},
    {"email": "editor@peblo.tv", "password": "editor123", "role": "editor"},
]


def _upsert_users(db: Session) -> None:
    for u in _DEFAULT_USERS:
        if not db.query(User).filter_by(email=u["email"]).first():
            db.add(
                User(
                    email=u["email"],
                    hashed_password=_pwd_context.hash(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
            )
    db.commit()


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def run_seed(
    db: Session,
    storage: LocalDiskStorage,
    assets_dir: str | Path,
    seed_rows: list[dict],
    ref_data: dict,  # noqa: ARG001 (reserved for future validation)
) -> dict:
    """
    Load seed_rows into the database idempotently.
    Returns a summary dict with counts of inserted/skipped/issues.
    """
    assets_dir = Path(assets_dir)

    # -- Discover which good assets are physically present on disk
    available_asset_paths: dict[str, Path] = {}
    for kind, filename in _GOOD_ASSET_FILES.items():
        p = assets_dir / filename
        if p.exists():
            available_asset_paths[kind] = p
        else:
            print(f"[seed] WARNING: good asset not found: {p}")

    # -- Group rows by slug → show
    shows_map: dict[str, dict] = {}
    for row in seed_rows:
        slug = row["slug"]
        if slug not in shows_map:
            shows_map[slug] = {
                "title": row["show_title"],
                "synopsis": row["synopsis"],
                "section": row.get("section"),
                "categories": list(row.get("categories", [])),
                "episodes": [],
            }
        shows_map[slug]["episodes"].append(row)

    summary = {
        "shows_inserted": 0,
        "seasons_inserted": 0,
        "episodes_inserted": 0,
        "artwork_inserted": 0,
        "content_issues_inserted": 0,
        "episodes_skipped_duplicate": 0,
    }

    # -- Track (content_group, language) seen in THIS seed run
    seen_cg_lang: dict[tuple[str, str], str] = {}  # (cg, lang) → episode_id str

    for slug, show_data in shows_map.items():
        episode_rows = show_data["episodes"]

        # ---- Infer show status (documented rule above) ----
        statuses = [r["status"] for r in episode_rows]
        inferred_status = "published" if any(s == "published" for s in statuses) else "draft"

        # ---- Upsert show ----
        show = db.query(Show).filter_by(slug=slug).first()
        if show is None:
            show = Show(
                title=show_data["title"],
                slug=slug,
                synopsis=show_data["synopsis"],
                section=show_data["section"],
                status=inferred_status,
            )
            db.add(show)
            db.flush()
            summary["shows_inserted"] += 1

            # Categories (only on insert — CRUD will manage updates)
            for cat in show_data["categories"]:
                db.add(ShowCategory(show_id=show.id, category=cat))
            db.flush()

        # ---- Determine show-level artwork availability ----
        # Poster/banner belong to the show. Create them if ANY episode
        # in this show lists the kind AND the asset actually exists.
        show_artwork_kinds: set[str] = set()
        for row in episode_rows:
            for kind in row.get("artwork_available", []):
                if kind in ("poster", "banner"):
                    show_artwork_kinds.add(kind)

        # ---- Group episodes by season ----
        seasons_map: dict[int, list[dict]] = {}
        for row in episode_rows:
            sn = row["season_number"]
            seasons_map.setdefault(sn, []).append(row)

        for season_number, ep_rows in seasons_map.items():
            # ---- Upsert season ----
            season = (
                db.query(Season)
                .filter_by(show_id=show.id, season_number=season_number)
                .first()
            )
            if season is None:
                season = Season(show_id=show.id, season_number=season_number)
                db.add(season)
                db.flush()
                summary["seasons_inserted"] += 1

            for row in ep_rows:
                cg = row["content_group"]
                lang = row["language"]
                ep_id_str = row["episode_id"]
                key = (cg, lang)

                if key in seen_cg_lang:
                    # ---- DUPLICATE detected ----
                    # Store in content_issues if not already recorded
                    already = (
                        db.query(ContentIssue)
                        .filter_by(
                            source_episode_id=ep_id_str,
                            issue_type="duplicate_content_group_language",
                        )
                        .first()
                    )
                    if already is None:
                        first_id = seen_cg_lang[key]
                        db.add(
                            ContentIssue(
                                source_episode_id=ep_id_str,
                                issue_type="duplicate_content_group_language",
                                severity="blocking",
                                message=(
                                    f"Duplicate (content_group={cg!r}, language={lang!r}). "
                                    f"First accepted occurrence: {first_id}. "
                                    f"This row (episode_id={ep_id_str!r}) was rejected "
                                    f"to preserve the DB UNIQUE constraint."
                                ),
                                raw_data=row,
                                created_at=datetime.now(timezone.utc),
                            )
                        )
                        summary["content_issues_inserted"] += 1
                    summary["episodes_skipped_duplicate"] += 1
                    continue

                seen_cg_lang[key] = ep_id_str

                # ---- Idempotency check ----
                if db.query(Episode).filter_by(content_group=cg, language=lang).first():
                    continue  # already in DB from a previous seed run

                # ---- Insert episode ----
                episode = Episode(
                    season_id=season.id,
                    content_group=cg,
                    language=lang,
                    title=row["episode_title"],
                    episode_number=row["episode_number"],
                    duration_seconds=row.get("duration_seconds"),
                    status=row["status"],
                )
                db.add(episode)
                db.flush()
                summary["episodes_inserted"] += 1

                # ---- Episode thumbnail artwork ----
                # Rule: create ONLY if "thumbnail" in artwork_available AND asset exists
                artwork_available = row.get("artwork_available", [])
                if "thumbnail" in artwork_available and "thumbnail" in available_asset_paths:
                    thumb_path = available_asset_paths["thumbnail"]
                    storage_key = f"episodes/{episode.id}/thumbnail{thumb_path.suffix}"
                    if not storage.exists(storage_key):
                        storage.put(
                            storage_key,
                            thumb_path.read_bytes(),
                            _CONTENT_TYPE.get(thumb_path.suffix.lower(), "image/jpeg"),
                        )
                    w, h, sz, chk = _img_info(str(thumb_path))
                    db.add(
                        Artwork(
                            episode_id=episode.id,
                            kind="thumbnail",
                            storage_key=storage_key,
                            width=w,
                            height=h,
                            size_bytes=sz,
                            checksum=chk,
                        )
                    )
                    summary["artwork_inserted"] += 1
                # If artwork_available is [] or thumbnail not in list → NO record created
                # ep_0036 falls into this branch, remains without thumbnail,
                # and will appear in the blocking validation report.

        # ---- Show-level artwork (poster / banner) ----
        for kind in ("poster", "banner"):
            if kind not in show_artwork_kinds:
                continue
            if kind not in available_asset_paths:
                continue
            existing = (
                db.query(Artwork).filter_by(show_id=show.id, kind=kind).first()
            )
            if existing:
                continue
            asset_path = available_asset_paths[kind]
            storage_key = f"shows/{show.id}/{kind}{asset_path.suffix}"
            if not storage.exists(storage_key):
                storage.put(
                    storage_key,
                    asset_path.read_bytes(),
                    _CONTENT_TYPE.get(asset_path.suffix.lower(), "image/jpeg"),
                )
            w, h, sz, chk = _img_info(str(asset_path))
            db.add(
                Artwork(
                    show_id=show.id,
                    kind=kind,
                    storage_key=storage_key,
                    width=w,
                    height=h,
                    size_bytes=sz,
                    checksum=chk,
                )
            )
            summary["artwork_inserted"] += 1

    db.commit()
    return summary


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

def main() -> None:
    seed_data_path = Path(os.environ.get("SEED_DATA_PATH", "/seed/seed_shows.json"))
    ref_json_path = Path(os.environ.get("REFERENCE_JSON_PATH", "/seed/reference.json"))
    assets_dir = Path(os.environ.get("SEED_ASSETS_DIR", "/seed/assets"))
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://peblo:peblo@localhost:5432/peblodb"
    )
    storage_root = os.environ.get("STORAGE_ROOT", "./storage")
    storage_base_url = os.environ.get("STORAGE_BASE_URL", "http://localhost:8000/media")

    # Fallback paths for local dev (running from repo root)
    if not seed_data_path.exists():
        local = Path(__file__).parent / "seed_shows.json"
        if local.exists():
            seed_data_path = local
    if not ref_json_path.exists():
        local = Path(__file__).parent / "reference.json"
        if local.exists():
            ref_json_path = local
    if not assets_dir.exists():
        local = Path(__file__).parent / "assets"
        if local.exists():
            assets_dir = local

    seed_rows = json.loads(seed_data_path.read_text(encoding="utf-8"))
    ref_data = json.loads(ref_json_path.read_text(encoding="utf-8"))

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    storage = LocalDiskStorage(root=storage_root, base_url=storage_base_url)

    with SessionLocal() as db:
        print("[seed] Creating default users …")
        _upsert_users(db)
        print("[seed] Loading shows/seasons/episodes …")
        summary = run_seed(db, storage, assets_dir, seed_rows, ref_data)

    print("[seed] Done.")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
