# Foyre Documentation

Start here. This page explains **what validation pipelines are**, **how to
use them**, and **where to find more detail**.

> New to Foyre overall? See the project [README](../README.md) first.

---

## Validation pipelines in one minute

When someone asks to deploy an AI app, Foyre can give them an **isolated
test cluster** (a "validation environment") to deploy into. A **validation
pipeline** then runs a set of automated **checks** against whatever they
actually deployed there — and attaches the results to the request so a
reviewer can approve with evidence instead of guesswork.

A pipeline is just an ordered list of **steps**. Each step is one check:
take an inventory of what's running, review its Kubernetes security
settings, scan its container images, enforce a policy, or run your own
custom check. Each step comes back **passed / warning / failed**, and the
overall run can **warn or block approval** based on rules an admin sets.

```
request  →  validation environment (deploy the app)  →  run pipeline  →  evidence  →  approve / reject
```

That's it. Everything below is detail.

## How a run flows

1. A requester provisions a validation environment and deploys their app.
2. A **reviewer** clicks **Run validation pipeline** on the request.
3. Foyre runs each step against the environment, collecting results +
   downloadable **evidence** (inventory JSON, scan reports, logs).
4. The run gets an overall status and an **approval impact**:
   `none` (fine), `warning` (look first), or `blocked`.
5. Approval respects that impact — a blocked run must be fixed (re-run) or
   overridden by a reviewer with a recorded reason.

## How to use pipelines

**If you're a reviewer (running a pipeline):**
→ Follow [Run a Validation Pipeline Against an AI Workload](tutorials/run-validation-pipeline.md).
It walks the whole flow: create the environment, deploy a sample workload,
run the default pipeline, read the results, download evidence, and
understand approval blocking/override.

**If you're an admin (defining what gets checked):**
→ See [Configure Validation Pipelines](admin/configure-validation-pipelines.md).
Foyre ships a default pipeline; this covers editing it, the step types you
can use, and the approval policy toggles. The easiest ways to add your own
checks, in order of effort:

1. **Policy checks (`builtin.policy`)** — pick from curated rules (no
   privileged containers, require resource limits, allowed registries…) in
   YAML. No code, no container.
2. **Inline script (`custom.script`)** — paste a bash/python snippet; it
   runs in a bundled image. No container to build.
3. **Bring your own container (`custom.kubernetes_job`)** — run any image;
   exit non-zero to fail, optionally emit richer findings.

**If you're integrating via API:**
→ See [Validation Pipeline API](api/validation-pipeline.md).

**If you're a contributor adding a built-in step type to Foyre itself:**
→ See [Build (Contribute) a Validation Step](dev/build-a-validation-step.md).

## All the docs

| Doc | For | Covers |
|---|---|---|
| [Validation Pipelines Overview](concepts/validation-pipelines.md) | Everyone | Concepts, objects, how runs + gating work |
| [Run a Validation Pipeline](tutorials/run-validation-pipeline.md) | Reviewers | Step-by-step usage (the main "how to use") |
| [Configure Validation Pipelines](admin/configure-validation-pipelines.md) | Admins | Authoring YAML, step types/tiers, chart config, approval policy |
| [Validation Pipeline API](api/validation-pipeline.md) | Integrators | Endpoints + curl examples |
| [Build a Validation Step](dev/build-a-validation-step.md) | Contributors | Adding native step types / scanners |
| [Extensibility Design](dev/validation-extensibility-design.md) | Maintainers | Architecture / ADR (not needed to use Foyre) |

**Most people want the [tutorial](tutorials/run-validation-pipeline.md)
(to run one) or the [admin guide](admin/configure-validation-pipelines.md)
(to configure one).**
