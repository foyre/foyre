"""Regression: /healthz must stay ahead of the SPA catch-all."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_204_without_static_dir() -> None:
    app = create_app()
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 204


def test_healthz_204_with_static_dir_and_spa(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "assets").mkdir()
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    app = create_app()
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 204
