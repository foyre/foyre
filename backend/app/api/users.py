"""Endpoints that act on the current user's own profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.passwords import PasswordTooLong, hash_password, verify_password
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChange, UserOut

router = APIRouter()


@router.post("/me/password", response_model=UserOut)
def change_my_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is incorrect")
    try:
        user.password_hash = hash_password(body.new_password)
    except PasswordTooLong as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
