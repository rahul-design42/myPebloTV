"""Tests for Phase 3A CRUD APIs."""
import pytest
from app.models import Show, Season, Episode, User

def test_crud_shows_admin(client, admin_token, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Create Show
    payload = {
        "title": "Test Show CRUD",
        "slug": "test-show-crud",
        "synopsis": "A test show",
        "section": "featured",
        "status": "draft",
        "categories": ["Comedy"]
    }
    r = client.post("/admin/shows", json=payload, headers=headers)
    assert r.status_code == 201
    show_id = r.json()["id"]

    # 2. Get Show
    r = client.get(f"/admin/shows/{show_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Test Show CRUD"
    assert r.json()["categories"] == ["Comedy"]

    # 3. Update Show
    r = client.put(f"/admin/shows/{show_id}", json={"title": "Updated Show CRUD"}, headers=headers)
    assert r.status_code == 200

    r = client.get(f"/admin/shows/{show_id}", headers=headers)
    assert r.json()["title"] == "Updated Show CRUD"

    # 4. List Shows with query params
    r = client.get("/admin/shows?q=Updated", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1

    # 5. Delete Show
    r = client.delete(f"/admin/shows/{show_id}", headers=headers)
    assert r.status_code == 204

    r = client.get(f"/admin/shows/{show_id}", headers=headers)
    assert r.status_code == 404


def test_crud_seasons_episodes(client, editor_token, db_session):
    headers = {"Authorization": f"Bearer {editor_token}"}
    
    # Setup Show
    r = client.post("/admin/shows", json={
        "title": "Season Test Show", "slug": "season-test", "status": "draft"
    }, headers=headers)
    show_id = r.json()["id"]

    # 1. Create Season
    r = client.post(f"/admin/shows/{show_id}/seasons", json={"season_number": 1}, headers=headers)
    assert r.status_code == 201
    season_id = r.json()["id"]

    # Create another season
    r = client.post(f"/admin/shows/{show_id}/seasons", json={"season_number": 2}, headers=headers)
    assert r.status_code == 201
    season2_id = r.json()["id"]

    # Conflict on duplicate season_number
    r = client.post(f"/admin/shows/{show_id}/seasons", json={"season_number": 1}, headers=headers)
    assert r.status_code == 400

    # List Seasons
    r = client.get(f"/admin/shows/{show_id}/seasons", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["seasons"]) == 2

    # Update Season
    r = client.put(f"/admin/seasons/{season_id}", json={"season_number": 10}, headers=headers)
    assert r.status_code == 200

    # 2. Create Episode
    ep_payload = {
        "content_group": "ep-group-1",
        "language": "en",
        "title": "Ep 1",
        "episode_number": 1,
        "duration_seconds": 300,
        "status": "draft"
    }
    r = client.post(f"/admin/seasons/{season_id}/episodes", json=ep_payload, headers=headers)
    assert r.status_code == 201
    episode_id = r.json()["id"]

    # Duplicate content_group + language
    r = client.post(f"/admin/seasons/{season_id}/episodes", json=ep_payload, headers=headers)
    assert r.status_code == 400

    # List Episodes
    r = client.get(f"/admin/seasons/{season_id}/episodes", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["episodes"]) == 1

    # Update Episode
    r = client.put(f"/admin/episodes/{episode_id}", json={"title": "Updated Ep"}, headers=headers)
    assert r.status_code == 200

    # Try deleting season before episode -> should fail safely
    r = client.delete(f"/admin/seasons/{season_id}", headers=headers)
    assert r.status_code == 400
    assert "Delete episodes first" in r.json()["detail"]

    # Try deleting show before season -> should fail safely
    r = client.delete(f"/admin/shows/{show_id}", headers=headers)
    assert r.status_code == 400
    assert "Delete seasons first" in r.json()["detail"]

    # Delete Episode
    r = client.delete(f"/admin/episodes/{episode_id}", headers=headers)
    assert r.status_code == 204

    # Delete Season
    r = client.delete(f"/admin/seasons/{season_id}", headers=headers)
    assert r.status_code == 204
    
    # Delete Season 2
    r = client.delete(f"/admin/seasons/{season2_id}", headers=headers)
    assert r.status_code == 204

    # Delete Show
    r = client.delete(f"/admin/shows/{show_id}", headers=headers)
    assert r.status_code == 204


def test_auth_protection(client, editor_token):
    # No auth
    r = client.get("/admin/shows")
    assert r.status_code == 401

    headers = {"Authorization": f"Bearer {editor_token}"}
    
    # Editor CAN list shows
    r = client.get("/admin/shows", headers=headers)
    assert r.status_code == 200

    # Editor CANNOT publish
    r = client.post("/admin/catalog/publish", headers=headers)
    assert r.status_code == 403

    # Editor CANNOT see validation report
    r = client.get("/admin/validation-report", headers=headers)
    assert r.status_code == 403

