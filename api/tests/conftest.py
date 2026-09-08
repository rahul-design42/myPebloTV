"""
Pytest configuration and shared fixtures for Phase 1 tests.

Test database strategy:
  Uses a separate PostgreSQL database (peblodb_test) to avoid touching the
  development database.  Tables are created via SQLAlchemy create_all()
  (faster than alembic for the test suite) and torn down after the session.

  If TEST_DATABASE_URL is set it overrides the derived URL.

Seed strategy:
  A session-scoped fixture runs the seed loader once per test session against
  the test database.  Tests that check seed state use a nested transaction
  (savepoint) so each test can roll back without wiping the seeded data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# --------------------------------------------------------------------------
# Path setup — allow importing from api/ and seed/
# --------------------------------------------------------------------------
_repo_root = Path(__file__).parent.parent.parent
_api_dir = _repo_root / "api"
_seed_dir = _repo_root / "seed"

for _p in [str(_api_dir), str(_repo_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Base, User
from app.storage.local import LocalDiskStorage

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --------------------------------------------------------------------------
# Test database URL
# --------------------------------------------------------------------------

def _test_db_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = get_settings().DATABASE_URL
    # Replace the database name with <name>_test
    if "/" in base:
        parts = base.rsplit("/", 1)
        return f"{parts[0]}/peblodb_test"
    return base


# --------------------------------------------------------------------------
# Engine / session fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped engine pointing at the test database."""
    url = _test_db_url()
    engine = create_engine(url, pool_pre_ping=True)
    # Create all tables from SQLAlchemy metadata
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def _SessionLocal(test_engine):
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def db_session(_SessionLocal) -> Session:
    """
    Function-scoped DB session wrapped in a savepoint so each test rolls back.
    """
    connection = _SessionLocal().bind.connect()
    trans = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    yield session

    session.close()
    nested.rollback()
    trans.rollback()
    connection.close()


# --------------------------------------------------------------------------
# Seed fixture (session-scoped — run once, persists for all tests)
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seeded_engine(test_engine, tmp_path_factory):
    """Run the seed loader once against the test database."""
    from seed.seed_loader import run_seed, _upsert_users

    assets_dir = _seed_dir / "assets"
    seed_rows = json.loads((_seed_dir / "seed_shows.json").read_text())
    ref_data = json.loads((_seed_dir / "reference.json").read_text())

    storage_root = tmp_path_factory.mktemp("storage")
    storage = LocalDiskStorage(root=str(storage_root), base_url="http://testserver/media")

    SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with SessionLocal() as db:
        _upsert_users(db)
        run_seed(db, storage, assets_dir, seed_rows, ref_data)

    return test_engine


@pytest.fixture(scope="session")
def seeded_db_session(seeded_engine):
    """A plain session against the seeded test database (no rollback per test)."""
    SessionLocal = sessionmaker(bind=seeded_engine, autocommit=False, autoflush=False)
    with SessionLocal() as db:
        yield db


# --------------------------------------------------------------------------
# Default test users (inserted by seed; used independently here for safety)
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _ensure_users(test_engine):
    """Ensure default users exist in the test DB (idempotent)."""
    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        for email, password, role in [
            ("admin@peblo.tv", "admin123", "admin"),
            ("editor@peblo.tv", "editor123", "editor"),
        ]:
            if not db.query(User).filter_by(email=email).first():
                db.add(
                    User(
                        email=email,
                        hashed_password=_pwd_context.hash(password),
                        role=role,
                        is_active=True,
                    )
                )
        db.commit()


# --------------------------------------------------------------------------
# HTTP client + token fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(test_engine, _ensure_users):
    """TestClient with the DB overridden to use the test database."""
    SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client, email: str, password: str) -> str:
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(client):
    return _login(client, "admin@peblo.tv", "admin123")


@pytest.fixture(scope="session")
def editor_token(client):
    return _login(client, "editor@peblo.tv", "editor123")
