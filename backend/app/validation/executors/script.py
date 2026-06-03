"""custom.script executor — inline script tier.

Runs an admin-authored bash/python snippet (from the pipeline YAML) as a
Job inside the validation environment, using the bundled runner image —
no container to build. The script is delivered via a ConfigMap mounted at
/foyre/script/run and executed with the chosen interpreter.

Conventions (shared with custom.kubernetes_job):
  - /foyre/input  : upstream artifacts (read-only)
  - /foyre/output : write evidence here; the uploader sidecar ships it back
  - exit code     : 0 = passed, 2 = warning, other = failed
  - /foyre/output/result.json (optional) : rich normalized result

Gated by `validation_allow_inline_scripts`; requires `validation_runner_image`
(the script's runtime). Admin-only authoring already restricts who can
introduce scripts.
"""
from __future__ import annotations

from app.config import settings
from app.domain.enums import ValidationStepStatus
from app.validation.executors.kubernetes_job import run_container_job
from app.validation.types import StepContext, StepOutcome

_SCRIPT_PATH = "/foyre/script/run"
_INTERPRETER_CMD = {
    "bash": ["bash", _SCRIPT_PATH],
    "python": ["python3", _SCRIPT_PATH],
}


def run(ctx: StepContext) -> StepOutcome:
    if not settings.validation_allow_inline_scripts:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="Inline script steps are disabled by policy.",
            error_message="validation_allow_inline_scripts is false",
        )

    runner_image = settings.validation_runner_image
    if not runner_image:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="Inline scripts require a configured runner image.",
            error_message="validation_runner_image is not set",
        )

    config = ctx.config
    script = config.get("script")
    if not isinstance(script, str) or not script.strip():
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="custom.script is missing config.script.",
            error_message="config.script is required",
        )

    interpreter = config.get("interpreter", "bash")
    command = _INTERPRETER_CMD.get(interpreter)
    if command is None:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary=f"Unsupported interpreter '{interpreter}'.",
            error_message="interpreter must be 'bash' or 'python'",
        )

    return run_container_job(
        ctx,
        image=runner_image,
        command=command,
        args=None,
        env=config.get("env"),
        resources=config.get("resources"),
        namespace=config.get("namespace"),
        script_content=script,
    )
