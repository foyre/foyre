"""Thin DB access for intake requests."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.request import IntakeRequest


def _with_user_refs():
    """Eager-load `created_by` so response serialization avoids N+1."""
    return selectinload(IntakeRequest.created_by)


def get(db: Session, request_id: int) -> IntakeRequest | None:
    stmt = (
        select(IntakeRequest)
        .options(_with_user_refs())
        .where(IntakeRequest.id == request_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_for_owner(db: Session, owner_id: int) -> list[IntakeRequest]:
    stmt = (
        select(IntakeRequest)
        .options(_with_user_refs())
        .where(IntakeRequest.created_by_id == owner_id)
        .order_by(IntakeRequest.id.desc())
    )
    return list(db.execute(stmt).scalars())


def list_all(db: Session) -> list[IntakeRequest]:
    stmt = (
        select(IntakeRequest)
        .options(_with_user_refs())
        .order_by(IntakeRequest.id.desc())
    )
    return list(db.execute(stmt).scalars())


def save(db: Session, req: IntakeRequest) -> IntakeRequest:
    db.add(req)
    db.commit()
    db.refresh(req)
    return req
