"""Admin-only user management.

Guards:
  - An admin cannot demote themselves (change their own role away from admin).
  - An admin cannot deactivate themselves.
Both protect against accidental self-lockout. A "last admin on the system"
check is not enforced; organizations should maintain at least one additional
admin as operational policy.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.db import get_db
from app.deps import require_role
from app.domain.enums import Role
from app.models.user import User
from app.repositories import users as users_repo
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    return users_repo.list_all(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    if users_repo.get_by_username(db, body.username):
        raise HTTPException(status.HTTP_409_CONFLICT, "username already exists")
    return users_repo.create(
        db,
        User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            role=body.role.value,
            must_change_password=body.must_change_password,
        ),
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.admin)),
):
    target = users_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

    is_self = target.id == actor.id

    if body.role is not None:
        if is_self and body.role != Role.admin:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "admins cannot demote themselves"
            )
        target.role = body.role.value

    if body.is_active is not None:
        if is_self and not body.is_active:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "admins cannot deactivate themselves"
            )
        target.is_active = body.is_active

    return users_repo.save(db, target)
