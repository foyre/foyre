"""Admin endpoints for managing the configurable intake form schema."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.domain.enums import Role
from app.models.user import User
from app.schemas.form_schema import FormSchemaAdminBundle, FormSchemaIn
from app.services import form_schema_service

router = APIRouter()


@router.get("", response_model=FormSchemaAdminBundle)
def get_admin_form_schema(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    """Return the current schema, the default, and the locked core-field list."""
    return form_schema_service.get_admin_view(db)


@router.put("", response_model=FormSchemaAdminBundle)
def update_form_schema(
    body: FormSchemaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.admin)),
):
    return form_schema_service.save(db, user, body.model_dump(mode="python"))


@router.post("/reset", response_model=FormSchemaAdminBundle)
def reset_form_schema(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    """Drop the admin customization and restore the built-in default schema."""
    return form_schema_service.reset(db)
