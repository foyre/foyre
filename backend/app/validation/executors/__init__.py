"""Step executor registry.

Maps a step `type` string to the callable that runs it. The runner looks
up an executor here; if none is registered, the step is recorded as
`skipped` (so a pipeline referencing a not-yet-implemented type still
produces a clean run rather than erroring).

Chunk 3 registers the two built-in inspection steps. `builtin.image_scan`
and `custom.kubernetes_job` are intentionally NOT registered yet — they
land in chunk 4 via `register()`.
"""
from __future__ import annotations

from app.validation.executors.kubernetes_security import run as kubernetes_security_run
from app.validation.executors.workload_inventory import run as workload_inventory_run
from app.validation.types import ExecutorFn

_REGISTRY: dict[str, ExecutorFn] = {
    "builtin.workload_inventory": workload_inventory_run,
    "builtin.kubernetes_security": kubernetes_security_run,
}


def get_executor(step_type: str) -> ExecutorFn | None:
    return _REGISTRY.get(step_type)


def register(step_type: str, fn: ExecutorFn) -> None:
    """Register (or override) an executor. Used by later chunks to add
    image-scan / custom-job executors without editing this module."""
    _REGISTRY[step_type] = fn


def registered_types() -> list[str]:
    return sorted(_REGISTRY)
