"""Health-check endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.database import check_db_health

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict:
    """Always returns 200 OK. Used as a liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe")
def health_ready(response: Response) -> dict:
    """
    Returns 200 if the database is reachable, 503 otherwise.
    Used as a readiness probe — a load balancer should stop sending traffic
    until this returns 200.

    Alert on this endpoint: if /health/ready returns 503 for more than 30 s,
    page the on-call engineer — the API cannot serve requests.
    """
    if check_db_health():
        return {"status": "ready", "database": "ok"}
    response.status_code = 503
    return {"status": "not_ready", "database": "unreachable"}
