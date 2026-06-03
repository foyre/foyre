# Run a Validation Pipeline Against an AI Workload

> Part of the [Foyre docs](../README.md). New to pipelines? The
> [docs index](../README.md) has a one-minute explainer.

This tutorial walks through validating an AI workload end-to-end: from an
isolated validation environment, to deploying a sample workload, to running
the default validation pipeline and reading the evidence before approval.

## What validation pipelines are

A validation pipeline is a repeatable set of checks Foyre runs against a
workload deployed in a request's **validation environment** (an isolated
vcluster). It collects a workload inventory, reviews Kubernetes security
posture, scans container images, and can run your own custom checks —
attaching the results and raw evidence to the request.

## Why they matter

Approving an AI application from a ticket alone tells you what someone
*intends* to deploy. A validation pipeline tells you what *actually* runs:
which images, which privileges, which vulnerabilities. Reviewers approve
with evidence, and every run is recorded for audit.

## Prerequisites

- A Foyre instance with at least one **host cluster** connected (see the
  in-app host-cluster setup guide under **Administration → Validation
  environments**).
- A user with the `reviewer`, `architect`, or `admin` role (these can run
  pipelines). Requesters can view results but not trigger runs.
- The default pipeline **"Default AI Workload Validation"** is seeded
  automatically on install. An admin can add more under
  **Administration → Validation pipelines**.

## 1. Create (or reuse) a validation environment

1. Open a submitted request.
2. In **Validation environment**, click **Create isolated cluster**.
3. Wait for the status to become **Ready** (this can take a few minutes).
4. The request owner downloads the scoped kubeconfig from the same card.

## 2. Deploy a sample workload

Using the downloaded kubeconfig, deploy something into the environment.
For example:

```bash
export KUBECONFIG=./vcluster-req-123.yaml

kubectl create deployment rag-api --image=ghcr.io/example/rag-api:latest
kubectl create deployment redis --image=docker.io/redis:7
```

Anything you deploy here is what the pipeline will inspect.

## 3. Run the default validation pipeline

1. On the request page, find the **Validation pipeline** section.
2. (If more than one pipeline is enabled, pick one from the dropdown;
   otherwise the default is used.)
3. Click **Run validation pipeline**.

The run starts immediately and the panel polls for progress. The default
pipeline runs three steps:

- **Workload Inventory** — discovers your deployments, pods, images, and
  configuration.
- **Kubernetes Security Review** — flags risky settings.
- **Container Image Scan** — scans each discovered image with Trivy.

## 4. View validation results

When the run finishes you'll see a summary like:

```
Validation Pipeline: Default AI Workload Validation
Status: Failed
Checks: 1 passed, 1 warning, 1 failed
Approval Impact: Blocked
```

Each step is a card you can expand to see:

- a short summary and severity;
- findings grouped by severity (with the affected resource and a
  recommendation);
- timestamps;
- links to raw evidence artifacts.

## 5. Download evidence artifacts

Inside an expanded step card, click any **⬇ artifact** link (for example
`workload-inventory.json` or `scan-ghcr.io_example_rag-api_latest.json`) to
download the raw evidence. Artifacts follow the same access rules as the
request — anyone who can see the request can download them.

## 6. Understand pass / warning / fail status

| Step status | Meaning |
|---|---|
| **Passed** | No issues at this step. |
| **Warning** | Issues found, but not severe enough to block (per policy). |
| **Failed** | Serious issues found (e.g. critical CVEs, privileged container). |
| **Skipped** | Step disabled, or a step type not available in this version. |
| **Error** | The step couldn't run (e.g. scanner unavailable, timeout). |

The **Approval Impact** rolls these up:

- **No impact** — safe to approve.
- **Warning** — approve allowed, but review the warnings first.
- **Blocked** — approval is blocked until resolved or overridden.

## 7. Approval blocking and override

If the latest run's approval impact is **Blocked**, the **Approve** button
shows **"Approve (blocked)"**. Clicking it opens a dialog:

- If override is allowed by policy, enter a **reason** and click
  **Override and approve**. The override (and your reason) is recorded in
  the request history.
- If override is disabled by policy, you'll be told to resolve the
  blocking findings and re-run validation.

Re-running the pipeline after fixing issues updates the latest result and
the approval gate.

## Related

- [Docs index](../README.md)
- [Validation Pipelines Overview](../concepts/validation-pipelines.md)
- [Configure Validation Pipelines](../admin/configure-validation-pipelines.md)
- [Validation Pipeline API](../api/validation-pipeline.md)
