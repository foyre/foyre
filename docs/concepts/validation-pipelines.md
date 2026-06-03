# Validation Pipelines Overview

> **Just want to use pipelines?** Start at the [docs index](../README.md) —
> it has a one-minute explainer and points reviewers to the
> [tutorial](../tutorials/run-validation-pipeline.md) and admins to the
> [configuration guide](../admin/configure-validation-pipelines.md). This
> page is the conceptual reference.

Validation Pipelines let teams run repeatable checks against AI workloads
deployed in a Foyre validation environment. Pipelines can collect workload
inventory, inspect Kubernetes security posture, scan container images, run
custom checks, and attach evidence to the request before approval.

**Foyre turns AI workload approval into an evidence-backed workflow.**
Instead of approving an AI app from a ticket alone, reviewers can validate
what actually runs.

## What Foyre is (and isn't)

Foyre is **not** trying to replace every scanner. It is the orchestration
and evidence layer for AI workload validation:

- Foyre orchestrates validation steps and stores their results + artifacts
  against the request.
- Teams can use the built-in checks **or bring their own** scanners,
  scripts, and validation logic.
- The validation environment (an isolated vcluster) gives reviewers a safe
  place to inspect behavior before production approval.
- Pipelines make that process **repeatable and auditable**.

Built-in image scanning (Trivy) is included and useful, but it is just one
step type among many — and it is replaceable.

## The core objects

| Object | What it is |
|---|---|
| **Validation Pipeline** | A named, versioned, reusable definition of validation steps (authored as YAML). |
| **Validation Step** | One unit of work inside a pipeline — a built-in check or a custom containerized job. |
| **Validation Run** | One execution of a pipeline against a request's validation environment. Snapshots the pipeline definition so historical results never change. |
| **Validation Step Result** | The normalized outcome of one step in a run (status, severity, findings). |
| **Validation Artifact** | Evidence produced by a run/step (JSON, logs, scan results) — downloadable from the UI and API. |

## How a pipeline runs

1. A reviewer runs a pipeline against a request that has a **ready**
   validation environment.
2. Foyre connects to that environment using its stored, encrypted
   kubeconfig.
3. Steps execute in dependency order. Each step produces a normalized
   result and may emit raw artifacts.
4. The run aggregates step results into an overall status and an
   **approval impact** (`none`, `warning`, or `blocked`).
5. The approval flow uses that impact: a `blocked` run prevents approval
   unless a reviewer overrides it with a recorded reason.

## Step types

**Built-in checks** (maintained by Foyre):

- `builtin.workload_inventory` — enumerate deployed resources + metadata
  (never secret values).
- `builtin.kubernetes_security` — flag risky configuration (privileged
  containers, hostPath/hostNetwork, missing limits, root execution, risky
  capabilities).
- `builtin.image_scan` — scan discovered images for vulnerabilities
  (Trivy by default; the scanner is pluggable).
- `builtin.policy` — curated, declarative policy rules over the inventory
  (no code, no container).

**Bring your own logic** (easiest first):

- `builtin.policy` — pick curated rules in YAML.
- `custom.script` — paste a bash/python snippet; runs in a bundled image
  (no container to build).
- `custom.kubernetes_job` — run any container image; exit non-zero to fail,
  optionally emit a `result.json` for rich findings.

The custom tiers share one contract (`/foyre/input`, `/foyre/output`, exit
codes, `result.json` precedence) documented in the
[configuration guide](../admin/configure-validation-pipelines.md). Adding a
*new built-in step type* in Python is a contributor task — see
[Build a Validation Step](../dev/build-a-validation-step.md). Further types
(webhooks, SBOM, network egress, OPA/CEL policy engines, more scanners) can
be added without changing the pipeline runner.

## Failure policies and approval gating

Each step declares a **failure policy**:

| Policy | Effect when the step fails |
|---|---|
| `ignore` | Never affects the run status or approval. |
| `warn` | Surfaces a warning; does not block approval. |
| `block` | Marks the run failed and blocks approval (override-able). |

Administrators tune the gate with three policies:

- `requireValidationBeforeApproval` (default **false**)
- `blockApprovalOnFailedValidation` (default **true**)
- `allowValidationOverride` (default **true**)

## Where to go next

- [Docs index](../README.md) — start here / one-minute explainer.
- [Run a Validation Pipeline Against an AI Workload](../tutorials/run-validation-pipeline.md) — hands-on tutorial.
- [Configure Validation Pipelines](../admin/configure-validation-pipelines.md) — admin guide + YAML reference.
- [Build a Validation Step](../dev/build-a-validation-step.md) — extend pipelines with custom or native steps.
- [Validation Pipeline API](../api/validation-pipeline.md) — API reference with curl examples.
