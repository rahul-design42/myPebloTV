"""Validation report router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.user import User
from app.services.validator import get_validation_report

router = APIRouter(prefix="/admin", tags=["admin-validation"])


@router.get("/validation-report", summary="Blocking issues for publish")
def validation_report(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Returns all issues blocking publish plus non-blocking quality warnings.
    Admin-only.
    """
    return get_validation_report(db)
