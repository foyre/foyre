from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import service as auth
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn, TokenOut
from app.schemas.user import UserOut

router = APIRouter()


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    result = auth.login(db, body.username, body.password)
    if not result:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    user, token = result
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
