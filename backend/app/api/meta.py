from __future__ import annotations

from fastapi import APIRouter

from app.domain.form_schema import FORM_SCHEMA

router = APIRouter()


@router.get("/form-schema")
def form_schema() -> dict:
    return {"sections": FORM_SCHEMA}
