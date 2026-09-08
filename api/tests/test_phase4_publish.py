from __future__ import annotations

import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Show, Episode, PublishRun, ContentIssue

def test_editor_cannot_publish(client: TestClient, editor_token: str):
    headers = {"Authorization": f"Bearer {editor_token}"}
    resp = client.post("/admin/catalog/publish", headers=headers)
    assert resp.status_code == 403

def test_admin_publish_blocked_by_validation(client: TestClient, admin_token: str, seeded_db_session: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    get_cat = client.get("/catalog")
    assert get_cat.status_code == 200
    original_catalog = get_cat.json()

    # Attempt to publish
    resp = client.post("/admin/catalog/publish", headers=headers)
    assert resp.status_code == 400
    assert "Publish blocked:" in resp.json()["detail"]
    
    # Verify catalogue is unchanged
    get_cat2 = client.get("/catalog")
    assert get_cat2.json() == original_catalog

def test_admin_publish_succeeds_when_resolved(client: TestClient, admin_token: str, seeded_db_session: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    report = client.get("/admin/validation-report", headers=headers)
    assert report.status_code == 200
    data = report.json()
    
    for show in data["blocking"]["shows_without_section"]:
        client.put(f"/admin/shows/{show['show_id']}", json={"status": "draft"}, headers=headers)
        
    for item in data["blocking"]["missing_artwork"]:
        if item["level"] == "episode":
            client.put(f"/admin/episodes/{item['episode_id']}", json={"status": "draft"}, headers=headers)
        else:
            client.put(f"/admin/shows/{item['show_id']}", json={"status": "draft"}, headers=headers)
            
    for ep in data["blocking"]["missing_duration"]:
        client.put(f"/admin/episodes/{ep['episode_id']}", json={"status": "draft"}, headers=headers)
        
    seeded_db_session.query(ContentIssue).delete()
    seeded_db_session.commit()
        
    report2 = client.get("/admin/validation-report", headers=headers)
    for k, v in report2.json()["blocking"].items():
        assert len(v) == 0, f"Still have blockers in {k}: {v}"
        
    resp = client.post("/admin/catalog/publish", headers=headers)
    assert resp.status_code == 202
    assert resp.json()["status"] == "succeeded"
