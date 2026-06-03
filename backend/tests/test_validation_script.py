"""Tests for the custom.script inline-script tier (Chunk 5)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.domain.enums import ValidationStepStatus
from app.validation.executors import kubernetes_job, script
from app.validation.executors import INGEST_STEP_TYPES
from app.validation.types import StepContext
from app.services import validation_pipeline_service as svc


# ---------------------------------------------------------------------------
# Parser validation
# ---------------------------------------------------------------------------


def _yaml(step_block: str) -> str:
    return (
        "apiVersion: foyre.ai/v1alpha1\n"
        "kind: ValidationPipeline\n"
        "metadata:\n  name: p\n"
        "spec:\n  steps:\n" + step_block
    )


def test_script_step_parses():
    y = _yaml(
        "    - name: check\n"
        "      type: custom.script\n"
        "      config:\n"
        "        interpreter: bash\n"
        "        script: |\n"
        "          echo hi\n"
    )
    norm = svc.parse_and_validate(y)
    assert norm["steps"][0]["type"] == "custom.script"


def test_script_step_requires_script():
    y = _yaml("    - name: check\n      type: custom.script\n      config:\n        interpreter: bash\n")
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "config.script" in str(ei.value.detail)


def test_script_step_bad_interpreter():
    y = _yaml(
        "    - name: check\n"
        "      type: custom.script\n"
        "      config:\n"
        "        interpreter: ruby\n"
        "        script: 'echo hi'\n"
    )
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "interpreter" in str(ei.value.detail)


def test_custom_script_no_longer_planned():
    # It's a supported type now, so referencing it must not give the
    # "planned but not yet available" message.
    from app.domain.validation_steps import PLANNED_STEP_TYPES, SUPPORTED_STEP_TYPES

    assert "custom.script" in SUPPORTED_STEP_TYPES
    assert "custom.script" not in PLANNED_STEP_TYPES


def test_script_is_ingest_step_type():
    assert "custom.script" in INGEST_STEP_TYPES


# ---------------------------------------------------------------------------
# Manifest: script configmap mount
# ---------------------------------------------------------------------------


def test_manifest_mounts_script_configmap():
    m = kubernetes_job.build_job_manifest(
        name="j",
        namespace="ns",
        image="foyre-runner:test",
        command=["bash", "/foyre/script/run"],
        args=None,
        env=None,
        configmap_name="j-input",
        timeout_seconds=120,
        script_configmap_name="j-script",
    )
    spec = m["spec"]["template"]["spec"]
    vol_names = {v["name"] for v in spec["volumes"]}
    assert "foyre-script" in vol_names
    main = spec["containers"][0]
    mounts = {mt["name"]: mt for mt in main["volumeMounts"]}
    assert mounts["foyre-script"]["mountPath"] == "/foyre/script"
    assert mounts["foyre-script"]["readOnly"] is True


def test_manifest_without_script_has_no_script_volume():
    m = kubernetes_job.build_job_manifest(
        name="j",
        namespace="ns",
        image="img",
        command=None,
        args=None,
        env=None,
        configmap_name="j-input",
        timeout_seconds=120,
    )
    vol_names = {v["name"] for v in m["spec"]["template"]["spec"]["volumes"]}
    assert "foyre-script" not in vol_names


# ---------------------------------------------------------------------------
# Executor gating (no cluster needed — these all short-circuit)
# ---------------------------------------------------------------------------


def _ctx(config):
    return StepContext(
        run_id=1,
        step={"name": "check", "type": "custom.script", "config": config},
        kubeconfig_yaml="kc",
    )


def test_executor_errors_when_scripts_disabled(monkeypatch):
    monkeypatch.setattr(script.settings, "validation_allow_inline_scripts", False)
    out = script.run(_ctx({"script": "echo hi"}))
    assert out.status == ValidationStepStatus.error
    assert "disabled" in out.summary.lower()


def test_executor_errors_without_runner_image(monkeypatch):
    monkeypatch.setattr(script.settings, "validation_allow_inline_scripts", True)
    monkeypatch.setattr(script.settings, "validation_runner_image", "")
    out = script.run(_ctx({"script": "echo hi"}))
    assert out.status == ValidationStepStatus.error
    assert "runner image" in out.summary.lower()


def test_executor_errors_without_script(monkeypatch):
    monkeypatch.setattr(script.settings, "validation_allow_inline_scripts", True)
    monkeypatch.setattr(script.settings, "validation_runner_image", "foyre-runner:test")
    out = script.run(_ctx({"interpreter": "bash"}))
    assert out.status == ValidationStepStatus.error
    assert "config.script" in (out.error_message or "")


def test_executor_delegates_to_run_container_job(monkeypatch):
    monkeypatch.setattr(script.settings, "validation_allow_inline_scripts", True)
    monkeypatch.setattr(script.settings, "validation_runner_image", "foyre-runner:test")
    captured = {}

    def fake_run_container_job(ctx, **kwargs):
        captured.update(kwargs)
        from app.validation.types import StepOutcome

        return StepOutcome(status=ValidationStepStatus.passed, summary="ok")

    monkeypatch.setattr(script, "run_container_job", fake_run_container_job)
    out = script.run(_ctx({"interpreter": "python", "script": "print('hi')"}))
    assert out.status == ValidationStepStatus.passed
    assert captured["image"] == "foyre-runner:test"
    assert captured["command"] == ["python3", "/foyre/script/run"]
    assert captured["script_content"] == "print('hi')"
