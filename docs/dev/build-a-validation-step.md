# Build Your Own Validation Step

This guide explains how Foyre's validation pipelines execute and how to
extend them with your own checks. There are two ways to add a step,
depending on whether you can change Foyre's code:

1. **No code — `custom.kubernetes_job`.** Package your logic as a
   container image and Foyre runs it as a Job. Best for most teams.
2. **A native executor (code contribution).** Add a first-class step type
   in Python. Best for checks you want bundled with Foyre.

If you just want to *use* pipelines, see the
[tutorial](../tutorials/run-validation-pipeline.md) and the
[admin guide](../admin/configure-validation-pipelines.md). This document is
about *building* steps.

---

## How a pipeline runs

A pipeline is a YAML document stored in the database. At runtime it is a
list of **steps**, each with a `type`, a `config` block, a `failurePolicy`,
and optional `dependsOn` links. A pipeline definition is **data** — it
isn't executable on its own. The work is done by **executors** that the
runner looks up by step `type`.

When a reviewer triggers a run, the runner:

1. Snapshots the pipeline definition onto the run (so later edits never
   rewrite historical results), decrypts the validation environment's
   kubeconfig, and orders the steps topologically by `dependsOn`.
2. For each step, builds a `StepContext` and calls the registered executor
   under a per-step wall-clock timeout (in a worker thread).
3. Takes the executor's `StepOutcome`, persists it as a step result plus
   any artifacts, and stores the outcome in an in-memory `upstream` map
   keyed by step name so later steps can read it.
4. Aggregates every step's `(status, failurePolicy)` into the run's overall
   status and **approval impact** (`none` / `warning` / `blocked`).

Everything except the executor — DB writes, timeouts, status roll-up,
approval gating, history events, the UI — is the framework's job. An
executor stays small and focused.

---

## The contract: `StepContext` → `StepOutcome`

An executor is just a function:

```python
def run(ctx: StepContext) -> StepOutcome: ...
```

### What you get: `StepContext`

| Field / helper | Meaning |
|---|---|
| `ctx.run_id` | The validation run's id. |
| `ctx.step` | The normalized step definition (name, type, config, dependsOn, …). |
| `ctx.config` | Shortcut for `ctx.step["config"]` — your step's options. |
| `ctx.step_name` / `ctx.step_type` | Convenience accessors. |
| `ctx.kubeconfig_yaml` | The validation environment's kubeconfig (already decrypted). Use it to talk to the vcluster. |
| `ctx.upstream` | Outcomes of already-completed steps, keyed by step name. |
| `ctx.upstream_of_type("builtin.workload_inventory")` | Find a prior step's outcome by its type (respects `dependsOn`, falls back to scanning all upstream). |

### What you return: `StepOutcome`

| Field | Meaning |
|---|---|
| `status` | `passed` / `warning` / `failed` / `error` / `skipped`. |
| `severity` | `none` / `low` / `medium` / `high` / `critical`. |
| `summary` | One-line human-readable result (shown on the step card). |
| `findings` | List of `{severity, title, resource, message, recommendation}` dicts (rendered as a table). |
| `details` | Arbitrary JSON the UI can show without parsing artifacts. |
| `artifacts` | `ArtifactDraft[]` — evidence persisted and downloadable. |
| `error_message` | Set when `status` is `error`. |

An `ArtifactDraft` is `{name, artifact_type, content: bytes, content_type}`,
where `artifact_type` is one of `json | yaml | text | log | sarif | sbom |
scan_result`.

### Normalized finding shape

Findings are deliberately uniform across all step types so the UI and
reviewers see one format:

```json
{
  "severity": "high",
  "title": "Privileged container detected",
  "resource": "deployment/rag-api",
  "message": "Container api is configured with privileged=true.",
  "recommendation": "Remove privileged mode unless absolutely required."
}
```

---

## How steps share data

There is **no shared mutable state** between steps. A downstream step reads
an upstream step's `StepOutcome` from `ctx.upstream` — typically by parsing
an artifact the upstream emitted. For example, the Kubernetes security step
reads the inventory step's `workload-inventory.json`:

```python
inv = ctx.upstream_of_type("builtin.workload_inventory")
if inv:
    for art in inv.artifacts:
        if art.name == "workload-inventory.json":
            workloads = json.loads(art.content)["workloads"]
```

Declare the relationship with `dependsOn` in the pipeline YAML so ordering
is correct and intent is clear.

---

## Path 1 — No code: `custom.kubernetes_job`

If you can package your check as a container image, you don't need to touch
Foyre's code at all. An admin adds a step pointing at your image:

```yaml
- name: company-egress-check
  type: custom.kubernetes_job
  displayName: Company Egress Check
  failurePolicy: warn
  dependsOn: [workload-inventory]
  timeoutSeconds: 300
  config:
    image: registry.example.com/security/egress-checker:latest
    command: ["/app/check"]
    args: ["--input", "/foyre/input/workload-inventory.json"]
    # env: { KEY: value }
```

### The container contract

- **Inputs** from upstream steps (e.g. `workload-inventory.json`) are
  mounted **read-only at `/foyre/input`**.
- A scratch volume is mounted at `/foyre/output`.
- Your container **must print one JSON object to stdout** in the normalized
  result shape. Foyre reads the pod logs, extracts the last JSON object,
  and stores both the parsed result and the raw logs as artifacts:

```json
{
  "status": "passed | warning | failed | error",
  "severity": "none | low | medium | high | critical",
  "summary": "Short summary of the result",
  "findings": [
    {
      "severity": "medium",
      "title": "External API endpoint detected",
      "resource": "deployment/rag-api",
      "message": "Workload references api.openai.com.",
      "recommendation": "Confirm egress is approved for this endpoint."
    }
  ]
}
```

### What Foyre guarantees (guardrails)

The Job is built by Foyre, not by the admin, so it is hardened by
construction:

- `privileged`, `hostPath`, `hostNetwork`, and `hostPID` are never set.
- The service-account token is **not** mounted.
- All Linux capabilities are dropped; resource limits are applied.
- The Job runs inside the request's validation vcluster and is cleaned up
  afterward.

Admins supply only `image`, `command`, `args`, and `env`. Because only
admins author pipelines, only admin-approved images run as custom jobs.

This path works with any language or tool you can put in a container.

---

## Path 2 — A native executor (code contribution)

To add a first-class step type (e.g. `builtin.network_egress`, or a new
image scanner), you add three things. **None of them touch the runner.**

### Step 1: Register the type so the parser accepts it

Add an entry to `SUPPORTED_STEP_TYPES` in
`backend/app/domain/validation_steps.py`:

```python
"builtin.network_egress": StepTypeSpec(
    type="builtin.network_egress",
    display_name="Network Egress Review",
    description="Inspect workloads for external network egress.",
    builtin=True,
),
```

Until a type is registered here, the YAML parser rejects pipelines that
reference it. (If the name is in `PLANNED_STEP_TYPES`, the parser returns a
friendly "planned, not yet available" message instead of a generic error.)

### Step 2: Write the executor

Create `backend/app/validation/executors/network_egress.py`:

```python
from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation.types import ArtifactDraft, StepContext, StepOutcome


def run(ctx: StepContext) -> StepOutcome:
    config = ctx.config
    # Read upstream inventory if you depend on it:
    inv = ctx.upstream_of_type("builtin.workload_inventory")
    # ... do work, using ctx.kubeconfig_yaml to reach the vcluster ...

    findings = [...]            # normalized finding dicts
    status = ValidationStepStatus.warning if findings else ValidationStepStatus.passed
    severity = ValidationSeverity.medium if findings else ValidationSeverity.none

    return StepOutcome(
        status=status,
        severity=severity,
        summary=f"{len(findings)} egress finding(s).",
        findings=findings,
        details={"checked": ...},
        artifacts=[
            ArtifactDraft(
                name="network-egress.json",
                artifact_type="json",
                content=b"{...}",
                content_type="application/json",
            )
        ],
    )
```

Guidelines:

- Keep the testable logic in a **pure function** that takes plain data
  (e.g. a workloads list) and returns findings, so you can unit-test it
  without a cluster. The built-in `kubernetes_security` step does this with
  `analyze_workloads(...)`.
- Don't raise for "the workload has problems" — return a `failed`/`warning`
  outcome. Reserve exceptions for genuine execution failures; the runner
  converts an uncaught exception or a timeout into a step `error`.
- Never log or persist secret values. The inventory step records Secret
  **names only** — follow that rule.

### Step 3: Register the executor

Add it to the registry in
`backend/app/validation/executors/__init__.py`:

```python
from app.validation.executors.network_egress import run as network_egress_run

_REGISTRY = {
    ...,
    "builtin.network_egress": network_egress_run,
}
```

Or register it dynamically at import time without editing that file:

```python
from app.validation import executors
executors.register("builtin.network_egress", network_egress_run)
```

That's the entire extension surface. The runner, persistence, approval
gate, and UI need no changes.

---

## Sub-plugin: add an image scanner

`builtin.image_scan` has its own plug point so you can swap the scanner
(Grype, NeuVector, an internal service) without touching the image-scan
executor. A scanner implements the `ImageScanner` protocol from
`backend/app/validation/scanners/base.py`:

```python
from app.validation.scanners.base import ScanResult, VulnerabilityCounts


class GrypeScanner:
    name = "grype"  # the value admins put in step config.scanner

    def scan(self, image: str, config: dict) -> ScanResult:
        # run grype, parse output...
        return ScanResult(
            image=image,
            success=True,
            counts=VulnerabilityCounts(critical=0, high=2, medium=5),
            raw=b"<raw scanner json>",
        )
```

Register it:

```python
from app.validation import scanners
scanners.register(GrypeScanner())
```

Then a pipeline selects it per step:

```yaml
- name: image-scan
  type: builtin.image_scan
  config:
    scanner: grype
```

Keep the output parsing separate from the subprocess/API call (a static
`parse(raw) -> VulnerabilityCounts` method) so it's unit-testable, as the
bundled `TrivyScanner` does.

---

## The design in one picture

Three independent registries, each a one-line extension point:

| Registry | Location | Adds |
|---|---|---|
| Step types | `app/domain/validation_steps.py` → `SUPPORTED_STEP_TYPES` | What the YAML parser accepts |
| Executors | `app/validation/executors/__init__.py` → `_REGISTRY` (or `register()`) | What actually runs a step |
| Scanners | `app/validation/scanners` → `register()` | Image-scan backends |

Unregistered step types degrade gracefully (recorded as `skipped`), and an
executor's exceptions or timeouts become a step `error` — never a crashed
run.

---

## Testing your step

- **Pure logic** (findings from a data structure): call it directly with
  synthetic input. No cluster, no DB.
- **Executor shaping** (turning data into a `StepOutcome`): monkeypatch the
  cluster/inventory access and assert on the returned status / findings /
  artifacts.
- **End-to-end** (the runner): register a fake executor in `_REGISTRY`, run
  a pipeline synchronously, and assert the persisted step results +
  artifacts. See `backend/tests/test_validation_run_api.py` for the
  pattern.

---

## Related

- [Validation Pipelines Overview](../concepts/validation-pipelines.md)
- [Run a Validation Pipeline Against an AI Workload](../tutorials/run-validation-pipeline.md)
- [Configure Validation Pipelines](../admin/configure-validation-pipelines.md)
- [Validation Pipeline API](../api/validation-pipeline.md)
