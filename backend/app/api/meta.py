from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services import form_schema_service

router = APIRouter()


@router.get("/form-schema")
def form_schema(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Return the active intake form schema (admin custom or built-in default)."""
    return {"sections": form_schema_service.get_active_sections(db)}
