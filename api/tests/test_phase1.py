"""
Phase 1 test suite.

Covers:
  - Application startup (health endpoints)
  - Database connectivity
  - All tables created by migrations
  - JWT creation / role extraction
  - Authentication (login success / failure / me)
  - Role-based authorisation (editor cannot publish, admin can)
  - Storage backend (put / get / exists / url_for / atomic_pointer_write)
  - Seed idempotency
  - Duplicate content_group/language → content_issues table
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jose import jwt
from sqlalchemy import inspect, text

# Path setup (mirrors conftest.py)
_repo_root = Path(__file__).parent.parent.parent
_api_dir = _repo_root / "api"
for _p in [str(_api_dir), str(_repo_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ===========================================================================
# Health endpoints
# ===========================================================================

class TestHealthEndpoints:
    def test_liveness_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readiness_returns_200_when_db_ok(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "ok"


# ===========================================================================
# Database connectivity
# ===========================================================================

class TestDatabaseConnectivity:
    def test_engine_can_execute_query(self, test_engine):
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

    def test_all_expected_tables_exist(self, test_engine):
        inspector = inspect(test_engine)
        existing = set(inspector.get_table_names())
        required = {
            "users",
            "shows",
            "show_categories",
            "seasons",
            "episodes",
            "artwork",
            "publish_runs",
            "content_issues",
        }
        missing = required - existing
        assert not missing, f"Missing tables: {missing}"

    def test_episodes_unique_constraint_exists(self, test_engine):
        inspector = inspect(test_engine)
        unique_constraints = inspector.get_unique_constraints("episodes")
        names = {uc["name"] for uc in unique_constraints}
        assert "uq_episode_content_group_language" in names

    def test_artwork_check_constraint_exists(self, test_engine):
        """Verify the artwork ownership CHECK constraint is present."""
        inspector = inspect(test_engine)
        check_constraints = inspector.get_check_constraints("artwork")
        names = {cc["name"] for cc in check_constraints}
        assert "ck_artwork_ownership" in names


# ===========================================================================
# JWT / authentication
# ===========================================================================

class TestJWT:
    def test_create_token_contains_sub_and_role(self):
        from app.auth.jwt import create_access_token
        from app.config import get_settings
        settings = get_settings()
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"

    def test_extract_role_admin(self):
        from app.auth.jwt import create_access_token, extract_role
        token = create_access_token({"sub": "u1", "role": "admin"})
        assert extract_role(token) == "admin"

    def test_extract_role_editor(self):
        from app.auth.jwt import create_access_token, extract_role
        token = create_access_token({"sub": "u2", "role": "editor"})
        assert extract_role(token) == "editor"

    def test_extract_role_invalid_token(self):
        from app.auth.jwt import extract_role
        assert extract_role("not.a.token") is None

    def test_decode_expired_token_raises(self):
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt, JWTError
        from app.config import get_settings
        settings = get_settings()
        expired = jose_jwt.encode(
            {"sub": "u", "role": "editor", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        from app.auth.jwt import decode_access_token
        with pytest.raises(JWTError):
            decode_access_token(expired)


# ===========================================================================
# Authentication endpoints
# ===========================================================================

class TestAuthEndpoints:
    def test_login_admin_success(self, client):
        resp = client.post("/auth/login", data={"username": "admin@peblo.tv", "password": "admin123"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_editor_success(self, client):
        resp = client.post("/auth/login", data={"username": "editor@peblo.tv", "password": "editor123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", data={"username": "admin@peblo.tv", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/auth/login", data={"username": "nobody@peblo.tv", "password": "x"})
        assert resp.status_code == 401

    def test_me_with_admin_token(self, client, admin_token):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "admin@peblo.tv"
        assert body["role"] == "admin"

    def test_me_with_editor_token(self, client, editor_token):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {editor_token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "editor@peblo.tv"
        assert body["role"] == "editor"

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_garbage_token_returns_401(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 401


# ===========================================================================
# Role-based authorisation
# ===========================================================================

class TestAuthorisation:
    def test_editor_cannot_publish_gets_403(self, client, editor_token):
        resp = client.post(
            "/admin/catalog/publish",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_call_publish_endpoint(self, client, admin_token):
        """Admin should reach the handler (not be rejected for auth reasons)."""
        resp = client.post(
            "/admin/catalog/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # 202 = accepted by stub; anything other than 401/403 is correct here
        assert resp.status_code not in (401, 403)

    def test_editor_cannot_access_validation_report(self, client, editor_token):
        resp = client.get(
            "/admin/validation-report",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_access_validation_report(self, client, admin_token):
        resp = client.get(
            "/admin/validation-report",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    def test_unauthenticated_cannot_access_admin_shows(self, client):
        resp = client.get("/admin/shows")
        assert resp.status_code == 401

    def test_editor_can_list_shows(self, client, editor_token):
        resp = client.get(
            "/admin/shows",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert resp.status_code == 200


# ===========================================================================
# Storage backend
# ===========================================================================

class TestLocalDiskStorage:
    def test_put_and_get_roundtrip(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        s.put("a/b/file.bin", b"\x00\x01\x02", "application/octet-stream")
        assert s.get("a/b/file.bin") == b"\x00\x01\x02"

    def test_exists_true(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        s.put("exists.txt", b"hello", "text/plain")
        assert s.exists("exists.txt") is True

    def test_exists_false(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        assert s.exists("no_such_file.txt") is False

    def test_url_for(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        assert s.url_for("shows/abc/poster.jpg") == "http://localhost/media/shows/abc/poster.jpg"

    def test_get_missing_raises_file_not_found(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        with pytest.raises(FileNotFoundError):
            s.get("nope.bin")

    def test_atomic_pointer_write_creates_file(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        payload = json.dumps({"run_id": "abc-123"}).encode()
        s.atomic_pointer_write("pointers/current.json", payload)
        assert s.exists("pointers/current.json")
        assert s.get("pointers/current.json") == payload

    def test_atomic_pointer_write_is_idempotent(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        s.atomic_pointer_write("ptr.json", b'{"v": 1}')
        s.atomic_pointer_write("ptr.json", b'{"v": 2}')
        assert s.get("ptr.json") == b'{"v": 2}'

    def test_path_traversal_rejected(self, tmp_path):
        from app.storage.local import LocalDiskStorage
        s = LocalDiskStorage(root=str(tmp_path), base_url="http://localhost/media")
        with pytest.raises((ValueError, FileNotFoundError)):
            s.get("../../etc/passwd")


# ===========================================================================
# Seed — idempotency and content_issues
# ===========================================================================

class TestSeed:
    def test_seed_creates_expected_shows(self, seeded_db_session):
        from app.models import Show
        shows = seeded_db_session.query(Show).all()
        slugs = {s.slug for s in shows}
        expected_slugs = {
            "motis-many-lives",
            "tiny-tales-banyan-dadi",
            "discover-india-with-moti",
            "peblo-songs",
            "peblo-songs-lyrical",
            "curious-cubs",
            "number-nest",
            "rhyme-rangers",
        }
        assert expected_slugs == slugs

    def test_rhyme_rangers_has_null_section(self, seeded_db_session):
        from app.models import Show
        rr = seeded_db_session.query(Show).filter_by(slug="rhyme-rangers").first()
        assert rr is not None
        assert rr.section is None

    def test_season_zero_exists_in_db(self, seeded_db_session):
        """Season 0 must be stored in DB (exclusion is the publisher's job)."""
        from app.models import Season, Show
        moti = seeded_db_session.query(Show).filter_by(slug="motis-many-lives").first()
        s0 = (
            seeded_db_session.query(Season)
            .filter_by(show_id=moti.id, season_number=0)
            .first()
        )
        assert s0 is not None

    def test_duplicate_episode_in_content_issues(self, seeded_db_session):
        """ep_9001 must be in content_issues, NOT in episodes."""
        from app.models import ContentIssue, Episode
        # The duplicate must be rejected from episodes
        dup = (
            seeded_db_session.query(ContentIssue)
            .filter_by(
                source_episode_id="ep_9001",
                issue_type="duplicate_content_group_language",
            )
            .first()
        )
        assert dup is not None, "ep_9001 duplicate was not recorded in content_issues"
        assert dup.severity == "blocking"

        # And ep_9001 must NOT be in episodes
        ep9001_in_db = (
            seeded_db_session.query(Episode)
            .filter_by(
                content_group="motis-many-lives-s01e02",
                language="hi",
            )
            .count()
        )
        assert ep9001_in_db == 1, "Expected exactly one hi variant for motis-many-lives-s01e02"

    def test_ep_0036_has_no_thumbnail(self, seeded_db_session):
        """ep_0036 has artwork_available=[] → no thumbnail record should exist."""
        from app.models import Artwork, Episode
        ep = (
            seeded_db_session.query(Episode)
            .filter_by(content_group="discover-india-with-moti-s01e04", language="en")
            .first()
        )
        assert ep is not None
        thumb = (
            seeded_db_session.query(Artwork)
            .filter_by(episode_id=ep.id, kind="thumbnail")
            .first()
        )
        assert thumb is None, "ep_0036 should NOT have a thumbnail (artwork_available was [])"

    def test_seed_idempotent(self, seeded_engine, tmp_path):
        """Running the seed a second time must not change row counts."""
        import json
        from seed.seed_loader import run_seed, _upsert_users
        from app.models import Show, Episode, Artwork, ContentIssue
        from sqlalchemy.orm import sessionmaker
        from app.storage.local import LocalDiskStorage

        SessionLocal = sessionmaker(bind=seeded_engine, autocommit=False, autoflush=False)
        seed_rows = json.loads((_repo_root / "seed" / "seed_shows.json").read_text())
        ref_data = json.loads((_repo_root / "seed" / "reference.json").read_text())
        assets_dir = _repo_root / "seed" / "assets"
        storage = LocalDiskStorage(root=str(tmp_path), base_url="http://testserver/media")

        with SessionLocal() as db:
            before = {
                "shows": db.query(Show).count(),
                "episodes": db.query(Episode).count(),
                "artwork": db.query(Artwork).count(),
                "issues": db.query(ContentIssue).count(),
            }

        with SessionLocal() as db:
            run_seed(db, storage, assets_dir, seed_rows, ref_data)

        with SessionLocal() as db:
            after = {
                "shows": db.query(Show).count(),
                "episodes": db.query(Episode).count(),
                "artwork": db.query(Artwork).count(),
                "issues": db.query(ContentIssue).count(),
            }

        assert before == after, f"Seed not idempotent: before={before}, after={after}"

    def test_shows_have_poster_and_banner_artwork(self, seeded_db_session):
        """Shows with artwork_available listing poster/banner must have those records."""
        from app.models import Artwork, Show
        moti = seeded_db_session.query(Show).filter_by(slug="motis-many-lives").first()
        poster = seeded_db_session.query(Artwork).filter_by(show_id=moti.id, kind="poster").first()
        banner = seeded_db_session.query(Artwork).filter_by(show_id=moti.id, kind="banner").first()
        assert poster is not None
        assert banner is not None

    def test_users_created(self, seeded_db_session):
        from app.models import User
        admin = seeded_db_session.query(User).filter_by(email="admin@peblo.tv").first()
        editor = seeded_db_session.query(User).filter_by(email="editor@peblo.tv").first()
        assert admin is not None and admin.role == "admin"
        assert editor is not None and editor.role == "editor"
