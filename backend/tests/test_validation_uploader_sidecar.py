"""Tests for the uploader sidecar manifest injection + the standalone
uploader program's pure helpers (Chunk 4a)."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

from app.validation.executors import kubernetes_job


# ---------------------------------------------------------------------------
# Manifest: sidecar injection
# ---------------------------------------------------------------------------


def _base_kwargs(**over):
    kw = dict(
        name="foyre-val-1-step",
        namespace="foyre-validation",
        image="registry.example.com/checker:latest",
        command=["/app/check"],
        args=None,
        env=None,
        configmap_name="cm",
        timeout_seconds=300,
    )
    kw.update(over)
    return kw


def test_manifest_without_uploader_has_no_sidecar():
    m = kubernetes_job.build_job_manifest(**_base_kwargs())
    spec = m["spec"]["template"]["spec"]
    assert "initContainers" not in spec
    assert "terminationGracePeriodSeconds" not in spec


def test_manifest_with_uploader_injects_native_sidecar():
    m = kubernetes_job.build_job_manifest(
        **_base_kwargs(),
        uploader_image="zfeldstein/foyre-runner:test",
        ingest_url="http://foyre.foyre.svc.cluster.local:8000",
        ingest_token="tok",
        run_id=42,
    )
    spec = m["spec"]["template"]["spec"]
    assert spec["terminationGracePeriodSeconds"] == 60
    sidecars = spec["initContainers"]
    assert len(sidecars) == 1
    sc = sidecars[0]
    # Native sidecar = init container with restartPolicy Always.
    assert sc["restartPolicy"] == "Always"
    assert sc["image"] == "zfeldstein/foyre-runner:test"
    env = {e["name"]: e["value"] for e in sc["env"]}
    assert env["FOYRE_INGEST_URL"] == "http://foyre.foyre.svc.cluster.local:8000"
    assert env["FOYRE_INGEST_TOKEN"] == "tok"
    assert env["FOYRE_RUN_ID"] == "42"
    assert env["FOYRE_OUTPUT_DIR"] == "/foyre/output"
    # Sidecar shares the output workspace, read-only.
    mounts = {v["name"]: v for v in sc["volumeMounts"]}
    assert mounts["foyre-output"]["readOnly"] is True
    # Hardened.
    assert sc["securityContext"]["allowPrivilegeEscalation"] is False
    assert sc["securityContext"]["capabilities"]["drop"] == ["ALL"]


def test_manifest_partial_uploader_args_no_sidecar():
    # All three (image + url + token) are required; missing one → no sidecar.
    m = kubernetes_job.build_job_manifest(
        **_base_kwargs(),
        uploader_image="img",
        ingest_url="http://x",
        ingest_token=None,
    )
    assert "initContainers" not in m["spec"]["template"]["spec"]


def test_manifest_main_container_guardrails_unchanged():
    m = kubernetes_job.build_job_manifest(
        **_base_kwargs(),
        uploader_image="img",
        ingest_url="http://x",
        ingest_token="t",
        run_id=1,
    )
    spec = m["spec"]["template"]["spec"]
    assert spec["automountServiceAccountToken"] is False
    assert spec["hostNetwork"] is False
    main = spec["containers"][0]
    assert main["name"] == "validator"
    assert main["securityContext"]["privileged"] is False


# ---------------------------------------------------------------------------
# Standalone uploader program (loaded from deploy/runner/uploader.py)
# ---------------------------------------------------------------------------


def _load_uploader():
    # tests/ -> backend/ -> repo root
    path = Path(__file__).resolve().parents[2] / "deploy" / "runner" / "uploader.py"
    spec = importlib.util.spec_from_file_location("foyre_uploader", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_uploader_guess_artifact_type():
    up = _load_uploader()
    assert up.guess_artifact_type("a.json") == "json"
    assert up.guess_artifact_type("b.sarif") == "sarif"
    assert up.guess_artifact_type("c.log") == "log"
    assert up.guess_artifact_type("d.unknown") == "text"


def test_uploader_build_payload_collects_files_and_result(tmp_path):
    up = _load_uploader()
    (tmp_path / "result.json").write_text(json.dumps({"status": "warning", "summary": "s"}))
    (tmp_path / "report.sarif").write_text("{}")
    (tmp_path / "notes.txt").write_text("hello")

    payload = up.build_payload(str(tmp_path))

    names = {a["name"] for a in payload["artifacts"]}
    assert names == {"result.json", "report.sarif", "notes.txt"}
    # result.json parsed into the normalized result.
    assert payload["result"] == {"status": "warning", "summary": "s"}
    # Round-trip one artifact's bytes.
    notes = next(a for a in payload["artifacts"] if a["name"] == "notes.txt")
    assert base64.b64decode(notes["content_b64"]).decode() == "hello"


def test_uploader_build_payload_empty_dir(tmp_path):
    up = _load_uploader()
    payload = up.build_payload(str(tmp_path))
    assert payload["artifacts"] == []
    assert payload["result"] is None


def test_uploader_build_payload_invalid_result_json(tmp_path):
    up = _load_uploader()
    (tmp_path / "result.json").write_text("not json")
    payload = up.build_payload(str(tmp_path))
    # File still uploaded as an artifact, but result stays None.
    assert any(a["name"] == "result.json" for a in payload["artifacts"])
    assert payload["result"] is None
