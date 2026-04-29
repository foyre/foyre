from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRef


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    author_id: int
    author: UserRef | None = None
    body: str
    created_at: datetime
