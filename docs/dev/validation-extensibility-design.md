# Design: Validation Pipeline Extensibility

**Status:** Proposed (design only — no implementation yet)
**Audience:** Foyre maintainers + reviewers
**Supersedes framing in:** [Build Your Own Validation Step](build-a-validation-step.md)
(that guide will be re-scoped to "Contributing a Native Validation Step")

---

## 1. Context

Foyre runs validation pipelines against AI workloads deployed in a
per-request validation environment (a vcluster). A pipeline is a
declarative YAML document; each **step** has a `type`, and the runner
dispatches to an **executor** registered for that type. Today there are
four step types (`builtin.workload_inventory`, `builtin.kubernetes_security`,
`builtin.image_scan`, `custom.kubernetes_job`) and three extension
registries (step types, executors, image scanners).

This design does **not** change the pipeline composition model (the DAG of
steps with `dependsOn` + `failurePolicy`). That layer is already a
declarative DSL comparable to Argo/Tekton and is working well.

## 2. Problem

Adding a *custom check* is harder than it should be:

1. The documented "build your own" path is a **native Python executor**
   (register a type + write `run()` + register it + redeploy). That is a
   code contribution to Foyre and should never have been the user-facing
   answer. It makes the system look like it must be forked to add a check.
2. The intended bring-your-own path, `custom.kubernetes_job`, carries two
   friction taxes: you must **build and push a container image** *and*
   **emit a Foyre-specific normalized JSON to stdout**. For a trivial
   check, both are overkill.
3. There is **no no-code path** and **no no-build path**. Comparable tools
   (Jenkins `sh`, Tekton Tasks, Argo) let most users avoid both.

The composition DSL is fine; **task authoring** is the gap.

## 3. Goals / Non-goals

**Goals**

- Most custom checks require **no code and no image build**.
- Bring-your-own container becomes **easy** (exit-code semantics, no
  mandatory JSON).
- One **normalized result** + one **evidence convention** unify every tier.
- Preserve the current architecture, registries, and DB-blob artifact
  store; everything is additive and backward compatible.

**Non-goals**

- Inventing a new pipeline-orchestration DSL (already have one).
- Inventing a new policy/expression language (adopt CEL/OPA if/when needed).
- Object-storage evidence retention (future; keep the seam open).
- Live cluster querying for the policy tier in v1 (operate on the
  inventory artifact instead).

## 4. The tiered task-authoring model

The user-facing ladder, easiest first:

| Tier | Name | Author writes | Build image? | Real code? | Security surface |
|---|---|---|---|---|---|
| 1 | **Declarative policy checks** | YAML config (toggles + lists) | No | No | None (reads inventory) |
| 2 | **Inline script** | A shell/python snippet in YAML | No | A little | High (arbitrary exec) |
| 3 | **Bring-your-own container** | Image ref + relaxed contract | Yes | Maybe | Medium (their image) |
| 4 | **Native executor** | Python in the Foyre repo | n/a | Yes | Contributor-only |

Tier 4 stays, but is **reframed as a contributor mechanism**, not a user
feature. Tiers 1–3 are the user story.

## 5. The unifying abstractions

Two contracts make all tiers coherent. They are the heart of this design.

### 5.1 One normalized result

Every tier converges on the existing `StepOutcome` shape
(`status`, `severity`, `summary`, `findings[]`, `details`, `artifacts`).
Tiers differ only in **how the result is produced**:

- **Tier 1** — the policy engine computes it.
- **Tiers 2/3** — Foyre *derives* it from exit code + output (see 5.2).
- **Tier 4** — the executor returns it directly (today's behavior).

The change is: cheaper tiers may **derive** the result instead of being
**required to emit** it.

### 5.2 Result precedence for script/container tiers

A step's result is resolved in this order (first match wins):

1. **`/foyre/output/result.json`** — if present and valid, it is the
   authoritative normalized result (rich findings, severity, summary).
2. **A single JSON object on stdout** — back-compat with today's
   `custom.kubernetes_job` contract. Parsed as the normalized result.
3. **Exit code** — the simplest path:
   - `0` → `passed`
   - `2` → `warning`
   - any other "clean" nonzero → `failed`
   - non-graceful termination (timeout, OOMKill/137, image pull failure)
     → `error` (the check *couldn't run*, distinct from "the workload
     failed the check")

`stdout`/`stderr` are always captured as a `job-logs.txt` artifact and used
as the step `summary` when no richer result is provided.

> **Why precedence matters:** exit codes can't distinguish "ran and failed"
> from "couldn't run." `result.json` can. Keeping stdout-JSON in the chain
> preserves every pipeline authored against today's contract.

### 5.3 The workspace convention (`/foyre/input`, `/foyre/output`)

- **`/foyre/input`** (read-only): upstream artifacts (e.g.
  `workload-inventory.json`) are mounted here.
- **`/foyre/output`** (writable): **anything a step writes here is ingested
  as a validation artifact** — SARIF, SBOM, scan JSON, logs, screenshots,
  reports. This answers "where do users store evidence": they drop files in
  `/foyre/output`, no API call required. Mirrors Tekton/Argo workspaces.

## 6. The hard part: extracting `/foyre/output` from a finished pod

A completed container's filesystem is not readable after exit. This is the
central engineering problem and must be designed before tiers 2/3 ship.
Options considered:

| Approach | How | Works for BYO container? | Notes |
|---|---|---|---|
| **A. Injected sidecar uploader** | Foyre adds a sidecar that, after the main container exits, reads the shared `/foyre/output` emptyDir and POSTs files back to a scoped Foyre ingest endpoint. | **Yes** | Industry pattern (Tekton/Argo). Needs a short-lived, single-run upload token + reachable Foyre URL from the vcluster. |
| **B. Reader pod** | After the Job completes, a second short-lived pod mounts the same volume and streams files out. | Yes | Requires a persistent volume (emptyDir doesn't survive pod end); more moving parts. |
| **C. Entrypoint wrapper** | Foyre wraps the command to tar+emit `/foyre/output` to stdout with markers. | **No** (we don't control BYO entrypoints) | Fine for the **script tier** (Foyre owns the entrypoint); not for BYO container. |

**Recommendation:** Approach **A (injected sidecar uploader)** as the
general mechanism, because it's the only one that works for BYO container
without owning the entrypoint. The script tier can use the same sidecar (it
doesn't hurt) so there's one code path. The sidecar:

- shares an `emptyDir` workspace with the main container,
- waits for the main container to terminate,
- uploads `/foyre/output/*` + captured logs to a Foyre ingest endpoint
  authenticated with a **per-run, single-use token** scoped to that run's
  artifacts,
- reports the main container's exit code.

This also keeps artifact bytes flowing back to the Foyre API (and thus the
DB-blob store) without Foyre needing kubeconfig-level `pods/exec` or log
scraping gymnastics.

> **Decision needed:** confirm the sidecar-upload approach and the
> ingest-endpoint + token model before building tiers 2/3.

## 7. Tier designs

### 7.1 Tier 1 — declarative policy checks (`builtin.policy`)

A built-in step that evaluates **curated, parameterized rules over the
workload inventory artifact** (not the live cluster). Reuses the inventory
the existing step already produces — no new cluster access, deterministic,
unit-testable.

Illustrative config (conceptual, not final):

```yaml
- name: org-policy
  type: builtin.policy
  failurePolicy: block
  dependsOn: [workload-inventory]
  config:
    checks:
      no_privileged_containers: { severity: high }
      require_resource_limits:  { severity: low }
      deny_latest_tag:          { severity: medium }
      allowed_registries:
        severity: high
        registries: ["registry.example.com", "ghcr.io/acme"]
      required_labels:
        severity: low
        labels: ["app.kubernetes.io/owner"]
```

- Each check is a named, Foyre-maintained function exposed as **data
  config** (mirrors how `kubernetes_security` toggles work today).
- Produces normalized findings + a `policy-results.json` artifact.
- **No expression language in v1.** Covers ~80% of org policy.
- **Limited to what the inventory captures** — expand the inventory when a
  desired rule needs more data.

**Power mode (later, opt-in):** a rule list backed by **CEL** (sandboxed,
safe, has a Python lib) or **OPA/Rego** (shell out, industry standard).
Slots in as a mode of this step or a separate type. Not the default UX.

### 7.2 Tier 2 — inline script (`custom.script`)

Admin pastes a script directly in the pipeline YAML; Foyre runs it as a Job
in the vcluster using a **bundled hardened runner image** (bash + python +
`kubectl` + `jq`). No image to build.

Illustrative config:

```yaml
- name: egress-check
  type: custom.script
  failurePolicy: warn
  dependsOn: [workload-inventory]
  timeoutSeconds: 300
  config:
    interpreter: bash            # bash | python
    script: |
      jq -e '.workloads | all(.containers[]; ...)' /foyre/input/workload-inventory.json
      # exit 0 = pass, exit 2 = warning, other = fail
```

- Uses the **result precedence** (5.2) and **workspace convention** (5.3).
- The biggest Jenkins-like usability win.

### 7.3 Tier 3 — bring-your-own container (`custom.kubernetes_job`, relaxed)

Keep the existing type; **relax the contract** to the same conventions as
Tier 2:

- exit code → status (5.2),
- stdout → summary + log artifact,
- `/foyre/output/*` → artifacts,
- `result.json` / stdout-JSON optional for rich findings.

**Fully backward compatible:** pipelines that print normalized JSON to
stdout continue to work (precedence step 2).

### 7.4 Tier 4 — native executor (reframed)

Unchanged mechanism. Docs move under contributor guidance and stop being
the user-facing answer.

## 8. Security model

The inline-script tier (and to a lesser degree BYO container) introduces
arbitrary execution. Mitigations:

- **Authoring is admin-only** (pipelines already are). Only admin-approved
  scripts/images run.
- **Chart toggle to disable the script tier** entirely for stricter orgs
  (e.g. `validation.allowInlineScripts: false`).
- **Runner pod hardening:** no mounted service-account token, dropped
  capabilities, `allowPrivilegeEscalation: false`, resource limits,
  enforced timeout, restricted/again-no host-* (built by Foyre, same as the
  current custom-job guardrails).
- **Egress restriction** on the runner pod where the host cluster supports
  NetworkPolicy.
- **Secret-leak acknowledgment (important):** today's "Foyre never stores
  Secret values" guarantee holds because the inventory step is controlled.
  A script/container can read vcluster Secrets and write them to
  `/foyre/output` or stdout, which become stored artifacts. This must be:
  - documented as **operator responsibility**,
  - kept under the **same request-scoped authz** as all artifacts
    (already the case),
  - optionally flagged (script/container-tier artifacts marked as
    potentially sensitive), with redaction as a future enhancement.
  Do **not** let this regress silently — call it out in the tier's docs.
- **Runner image is a maintained artifact:** CVE patch cadence, supply
  chain, size budget, built in CI. Accept this ongoing cost explicitly.

## 9. Artifacts / evidence

- Storage stays **DB blobs** behind the existing `read_bytes()` seam.
- **Limits are required now** (not later): per-file size cap, per-run total
  cap, per-run file-count cap, content-type sniffing/allowlist. Without
  these, arbitrary `/foyre/output` writes can bloat the DB and API
  responses.
- Over-cap files are rejected (recorded as a truncated/omitted note on the
  run) rather than silently stored.
- **Future:** object storage (S3/MinIO) for enterprise retention — the
  `read_bytes()` / `storage_kind` seam already anticipates this; no caller
  changes when it lands.

## 10. Backward compatibility

- Existing `custom.kubernetes_job` pipelines (stdout normalized JSON)
  continue to work via precedence step 2.
- All new step types are additive; existing runs and their snapshots are
  untouched.
- The native-executor registry is unchanged; only its documentation
  framing changes.

## 11. Rollout / sequencing

The tiers are **not independent** — there is a dependency spine.

1. **Foundation:** the result precedence (5.2) + workspace + output
   extraction (6) + artifact limits (9). Ship by **relaxing
   `custom.kubernetes_job`** — smallest change that proves the foundation
   and makes BYO easier, backward compatibly.
2. **Tier 1 (`builtin.policy`)** — can proceed **in parallel** with (1); it
   shares almost nothing and has near-zero security surface. Highest ROI.
3. **Tier 2 (`custom.script`)** — after (1) (reuses the plumbing) and after
   the security work in (8) (runner image, RBAC, disable toggle, leak docs).
4. **Power/enterprise:** CEL/OPA mode; object-storage evidence.
5. **Docs reframe:** rename the native-executor guide to "Contributing a
   Native Validation Step"; lead users with tiers 1–3.

**If only two things ship:** (1) relaxed contract + output plumbing, and
(2) the curated policy tier. Together they deliver "bring any container,
easily" + "no-code checks" — the bulk of the perceived-complexity fix —
without taking on the runner-image and arbitrary-execution burden yet.

## 12. Open decisions

1. **Output extraction:** confirm sidecar-uploader (Approach A) + the
   per-run ingest token/endpoint design.
2. **Reachability:** can the vcluster reach the Foyre API to upload
   artifacts in all supported topologies? If not, fall back to a
   reader-pod or log-marker scheme for those topologies.
3. **Runner image:** base image, toolset (bash/python/kubectl/jq?),
   ownership of patching, and whether it's a separate published image or a
   variant of the Foyre image.
4. **Script tier default:** on or off by default in the chart?
5. **Policy v1 surface:** the exact set of curated checks to ship first.
6. **Secret handling:** flag/redact script-tier artifacts, or document-only
   for v1?

## 13. Summary

Keep the pipeline DSL. Stop selling native executors to users. Add a
no-code policy tier and a no-build script tier, relax the container
contract to exit-code semantics, and standardize "drop files in
`/foyre/output` for evidence." The result is Jenkins/Argo-like ergonomics
without inventing a new language — the genuinely hard work is the
finished-pod output extraction (§6) and the script-tier security model
(§8), and those should be designed and agreed before implementation.

---

## Related

- [Validation Pipelines Overview](../concepts/validation-pipelines.md)
- [Configure Validation Pipelines](../admin/configure-validation-pipelines.md)
- [Build Your Own Validation Step](build-a-validation-step.md) (to be re-scoped to contributor-only)
- [Validation Pipeline API](../api/validation-pipeline.md)
