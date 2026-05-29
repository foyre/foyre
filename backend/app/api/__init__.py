"""Aggregates all API routers under a single `api_router`."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    admin_form_schema,
    admin_users,
    auth,
    comments,
    host_clusters,
    meta,
    requests,
    users,
    validation_environments,
    validation_pipelines,
    validation_runs,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(requests.router, prefix="/requests", tags=["requests"])
api_router.include_router(comments.router, prefix="/requests", tags=["comments"])
api_router.include_router(
    validation_environments.router, prefix="/requests", tags=["validation"]
)
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin"])
api_router.include_router(
    host_clusters.router, prefix="/admin/host-clusters", tags=["admin"]
)
api_router.include_router(
    admin_form_schema.router, prefix="/admin/form-schema", tags=["admin"]
)
api_router.include_router(
    validation_pipelines.router, prefix="/validation/pipelines", tags=["validation"]
)
# Run + artifact routes use mixed path roots (/requests/... and
# /validation-runs/...), so they're registered without a shared prefix.
api_router.include_router(validation_runs.router, tags=["validation"])
