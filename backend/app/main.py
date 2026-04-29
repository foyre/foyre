"""FastAPI application factory and router wiring."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import api_router
from app.db import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title="Foyre", version="0.1.0")

    Base.metadata.create_all(bind=engine)

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
