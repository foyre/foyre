"""FastAPI application factory and router wiring."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.db import Base, engine


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve the bundled single-page app from `static_dir`.

    Behavior:
      - Hashed asset paths (e.g. /assets/*) are served verbatim by StaticFiles.
      - Any other GET that doesn't match an API route falls back to
        `index.html` so client-side routing (React Router) works on hard
        refresh and deep links.
      - Anything under /api/ is excluded from the fallback so unknown
        API paths still 404 cleanly.
    """
    index_path = static_dir / "index.html"
    if not index_path.is_file():
        return

    # Serve hashed assets directly.
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir), check_dir=False),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str, request: Request):
        # Any unhandled path under /api/ should be a real 404 (not the SPA).
        if full_path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

        # Try a literal file under static (favicon.ico, foyre-logo.png, etc.).
        candidate = (static_dir / full_path).resolve()
        try:
            candidate.relative_to(static_dir.resolve())
        except ValueError:
            # Path traversal attempt — refuse.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
        if candidate.is_file():
            return FileResponse(candidate)

        # Otherwise hand back the SPA shell.
        return FileResponse(index_path, media_type="text/html")


def create_app() -> FastAPI:
    app = FastAPI(title="Foyre", version="0.1.0")

    Base.metadata.create_all(bind=engine)

    app.include_router(api_router, prefix="/api")

    # If a built frontend has been placed at $STATIC_DIR (set by the production
    # Docker image / Helm chart), serve it from the same origin so a single
    # ingress/host can front the app.
    static_dir_env = os.environ.get("STATIC_DIR")
    if static_dir_env:
        _mount_spa(app, Path(static_dir_env))

    return app


app = create_app()


# Lightweight liveness probe for k8s / load balancers — distinct from the
# OpenAPI surface so it never gets accidentally caught up in route changes.
@app.get("/healthz", include_in_schema=False)
def _healthz() -> Response:
    return Response(status_code=204)
