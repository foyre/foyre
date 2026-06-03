#!/usr/bin/env python3
"""Foyre validation uploader sidecar.

Runs as a native sidecar (an init container with restartPolicy: Always)
alongside a validation job's main container, sharing the /foyre/output
workspace. When the main container finishes, the kubelet sends this
sidecar SIGTERM; we trap it, collect everything under /foyre/output, and
POST it to the Foyre ingest endpoint before exiting.

Standalone by design: stdlib only, NO imports from the Foyre app package
(this runs in the slim foyre-runner image, which doesn't carry app code).

Contract:
  - /foyre/output/result.json (if present + valid JSON object) becomes the
    step's normalized result.
  - Every regular file under /foyre/output is uploaded as an artifact.

Env:
  FOYRE_INGEST_URL    base URL, e.g. http://foyre.foyre.svc.cluster.local:8000
  FOYRE_INGEST_TOKEN  per-run ingest token (Bearer)
  FOYRE_RUN_ID        validation run id
  FOYRE_OUTPUT_DIR    workspace dir (default /foyre/output)
"""
from __future__ import annotations

import base64
import json
import os
import signal
import sys
import time
import urllib.request
from pathlib import Path

RESULT_FILENAME = "result.json"
_MAX_FILE_BYTES = 5 * 1024 * 1024  # mirror the server's per-file cap

_TYPE_BY_EXT = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".log": "log",
    ".txt": "text",
    ".sarif": "sarif",
    ".sbom": "sbom",
    ".spdx": "sbom",
}


def guess_artifact_type(filename: str) -> str:
    return _TYPE_BY_EXT.get(Path(filename).suffix.lower(), "text")


def build_payload(output_dir: str) -> dict:
    """Collect /foyre/output into an ingest request body. Pure + testable."""
    artifacts = []
    result = None
    root = Path(output_dir)
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if len(data) > _MAX_FILE_BYTES:
                # Skip oversized files; the server would reject them anyway.
                continue
            rel = str(path.relative_to(root))
            artifacts.append(
                {
                    "name": rel,
                    "artifact_type": guess_artifact_type(rel),
                    "content_type": "application/json"
                    if rel.endswith(".json")
                    else "text/plain",
                    "content_b64": base64.b64encode(data).decode("ascii"),
                }
            )
            if rel == RESULT_FILENAME:
                try:
                    obj = json.loads(data.decode("utf-8"))
                    if isinstance(obj, dict):
                        result = obj
                except (ValueError, UnicodeDecodeError):
                    pass
    return {"result": result, "artifacts": artifacts}


def _post(url: str, token: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - trusted internal URL
        resp.read()


def upload() -> None:
    base = os.environ.get("FOYRE_INGEST_URL", "").rstrip("/")
    token = os.environ.get("FOYRE_INGEST_TOKEN", "")
    run_id = os.environ.get("FOYRE_RUN_ID", "")
    output_dir = os.environ.get("FOYRE_OUTPUT_DIR", "/foyre/output")
    if not (base and token and run_id):
        print("uploader: missing FOYRE_INGEST_* env; nothing to do", file=sys.stderr)
        return
    payload = build_payload(output_dir)
    url = f"{base}/api/validation-ingest/{run_id}"
    try:
        _post(url, token, payload)
        print(f"uploader: posted {len(payload['artifacts'])} artifact(s) to {url}")
    except Exception as e:  # noqa: BLE001 - best-effort; the runner has a log fallback
        print(f"uploader: upload failed: {e}", file=sys.stderr)


def main() -> None:
    done = {"flag": False}

    def _handle(signum, _frame):
        if done["flag"]:
            return
        done["flag"] = True
        upload()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    # Idle until the kubelet signals us (after the main container exits).
    while not done["flag"]:
        time.sleep(1)


if __name__ == "__main__":
    main()
