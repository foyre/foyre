# Configure Validation Pipelines

This guide is for administrators. It covers creating and editing
validation pipelines, the pipeline YAML format, step types, failure
policies, approval gating, and security considerations.

> Only **admins** can create, edit, enable/disable, set-default, or delete
> pipelines. Reviewers/architects/admins can *run* them.

## What a validation pipeline is

A pipeline is a named, versioned, reusable definition of validation steps
that reviewers run against a request's validation environment. Foyre ships
with a default pipeline (**"Default AI Workload Validation"**); you can edit
it or add your own.

## How to create a pipeline

1. Go to **Administration → Validation pipelines**.
2. Click **New pipeline**.
3. Author the definition in YAML (see format below).
4. Click **Validate** to check it server-side, then **Create pipeline**.
5. Optionally check **Make this the default pipeline**.

## How to edit pipeline YAML

Click **Edit** on a pipeline row. The full YAML opens in the editor. Make
changes, **Validate**, then **Save changes**. Each save increments the
pipeline's version. Existing validation runs keep a snapshot of the
definition they used, so editing a pipeline never changes historical
results.

Other row actions: **Set default**, **Enable/Disable**, **Delete**.
Deleting a pipeline does not delete past runs.

## Pipeline format

```yaml
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: default-ai-workload-validation        # slug: [a-z][a-z0-9-]*
  displayName: Default AI Workload Validation
  description: Default validation pipeline for AI workloads.
spec:
  failurePolicy: warn                          # default policy for steps
  steps:
    - name: workload-inventory
      type: builtin.workload_inventory
      displayName: Workload Inventory
      required: true
      failurePolicy: warn
      timeoutSeconds: 120
      config:
        includeNamespaces: ["*"]
        excludeNamespaces: [kube-system]

    - name: kubernetes-security
      type: builtin.kubernetes_security
      displayName: Kubernetes Security Review
      required: true
      failurePolicy: block
      dependsOn: [workload-inventory]
      timeoutSeconds: 120
      config:
        denyPrivilegedContainers: true
        warnIfRunAsRoot: true
        warnIfMissingResourceLimits: true
        warnIfHostPathMounts: true
        warnIfHostNetwork: true

    - name: image-scan
      type: builtin.image_scan
      displayName: Container Image Scan
      required: true
      failurePolicy: block
      dependsOn: [workload-inventory]
      timeoutSeconds: 900
      config:
        scanner: trivy
        failOnCritical: true
        warnOnHigh: true
        ignoreUnfixed: false
```

### Pipeline fields

| Field | Meaning |
|---|---|
| `apiVersion` | Must be `foyre.ai/v1alpha1`. |
| `kind` | Must be `ValidationPipeline`. |
| `metadata.name` | Unique slug (`^[a-z][a-z0-9-]{0,62}$`). |
| `metadata.displayName` | Human-friendly name (defaults to `name`). |
| `metadata.description` | Optional description. |
| `spec.failurePolicy` | Default failure policy for steps that omit one. |
| `spec.steps` | Ordered list of steps (at least one). |

### Step fields

| Field | Meaning |
|---|---|
| `name` | Unique slug within the pipeline. |
| `type` | A supported step type (see below). |
| `displayName` | Optional label shown in the UI. |
| `description` | Optional description. |
| `enabled` | Default `true`. A disabled step is recorded as skipped. |
| `required` | Advisory flag stored with the result. |
| `dependsOn` | List of step names that must run first (no cycles). |
| `timeoutSeconds` | Per-step wall-clock timeout (1–3600). |
| `failurePolicy` | `ignore` \| `warn` \| `block`. |
| `config` | Step-type-specific options. |

## Step types

### `builtin.workload_inventory`

Enumerates resources in the validation environment and collects non-secret
metadata (images, securityContext, resource limits, volume types). Records
Secret/ConfigMap **names only**, never values.

`config`: `includeNamespaces` (glob list, default `["*"]`),
`excludeNamespaces` (glob list).

### `builtin.kubernetes_security`

Reviews the inventory for risky configuration. `config` toggles:
`denyPrivilegedContainers`, `warnIfRunAsRoot`,
`warnIfMissingResourceLimits`, `warnIfHostPathMounts`, `warnIfHostNetwork`.

### `builtin.image_scan`

Scans discovered images for vulnerabilities. `config`: `scanner`
(default `trivy`), `failOnCritical` (default true), `warnOnHigh`
(default true), `ignoreUnfixed` (default false). The scanner is
pluggable — additional scanners can be registered without changing the
pipeline.

### `builtin.policy` — curated declarative checks (no code)

Evaluates a curated set of named rules over the workload inventory — no
container, no script. The easiest way to add organization policy.

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
      banned_capabilities:
        severity: high
        capabilities: ["SYS_ADMIN", "NET_ADMIN", "ALL"]
      host_path_mounts: { severity: high }
```

Available checks: `no_privileged_containers`, `require_resource_limits`,
`deny_latest_tag`, `allowed_registries`, `required_labels`,
`banned_capabilities`, `host_path_mounts`. Omit `config.checks` to run a
sensible default set. Each check's `severity` is overridable.

### Bring-your-own logic: the shared step contract

`custom.script` and `custom.kubernetes_job` both run inside the validation
environment and share one contract:

- **`/foyre/input`** (read-only): upstream artifacts (e.g.
  `workload-inventory.json`).
- **`/foyre/output`** (writable): anything written here becomes a
  downloadable evidence artifact.
- **Exit code** drives the result: `0` = passed, `2` = warning, other
  non-zero = failed; a timeout / OOMKill = error.
- **Optional `/foyre/output/result.json`** for rich findings — when present
  it takes precedence over the exit code:

  ```json
  {
    "status": "passed | warning | failed | error",
    "severity": "none | low | medium | high | critical",
    "summary": "Short summary",
    "findings": [
      { "severity": "medium", "title": "...", "resource": "deployment/rag-api",
        "message": "...", "recommendation": "..." }
    ]
  }
  ```

Result precedence: `result.json` → a single JSON object on stdout
(back-compat) → exit code. Evidence is pushed back to Foyre by an injected
**uploader sidecar** (requires the validation cluster to reach the Foyre
API — see Configuration). Without that wiring, steps run **log-only**
(exit code + stdout; no `/foyre/output` evidence).

### `custom.script` — inline script (no build)

Paste a `bash` or `python` script directly in the pipeline; it runs in the
bundled runner image — no container to build.

```yaml
- name: egress-check
  type: custom.script
  failurePolicy: warn
  dependsOn: [workload-inventory]
  timeoutSeconds: 300
  config:
    interpreter: bash          # bash | python
    script: |
      jq -e '...' /foyre/input/workload-inventory.json
      # exit 0 = pass, 2 = warning, other = fail
```

Requires `validation.runnerImage` and `validation.allowInlineScripts: true`.

### `custom.kubernetes_job` — bring your own container

Runs your own container image as a Kubernetes Job, following the shared
contract above.

```yaml
- name: custom-company-check
  type: custom.kubernetes_job
  displayName: Company Policy Check
  failurePolicy: warn
  dependsOn: [workload-inventory]
  timeoutSeconds: 300
  config:
    image: registry.example.com/security/company-ai-checker:latest
    command: ["/app/check"]
    args: ["--input", "/foyre/input/workload-inventory.json"]
    # env: { KEY: value }
```

A plain container that simply exits non-zero is enough — emitting
`result.json` is optional, for richer findings.

## How failure policies work

| Step result | `ignore` | `warn` | `block` |
|---|---|---|---|
| passed / skipped | no impact | no impact | no impact |
| warning | no impact | run ≥ warning, approval ≥ warning | run ≥ warning, approval ≥ warning |
| failed / error | no impact | run ≥ warning, approval ≥ warning | run = failed, approval = **blocked** |

The run's overall **approval impact** is the worst across its steps.

## How approval gates work

Under **Administration → Validation pipelines → Approval policy**:

| Toggle | Default | Effect |
|---|---|---|
| `requireValidationBeforeApproval` | off | When on, a request can't be approved until a validation run has completed. |
| `blockApprovalOnFailedValidation` | on | When on, a `blocked` run prevents approval. |
| `allowValidationOverride` | on | When on, a reviewer can override a blocked approval with a reason. |

When an approval is blocked, the reviewer either resolves the findings and
re-runs, or (if allowed) overrides with a required reason. Overrides and
blocked attempts are recorded in the request history.

## Configuration (Helm)

Evidence push (the uploader sidecar) and inline scripts require two chart
values; without them, container/script steps run in **log-only** mode
(exit code + stdout, no `/foyre/output` evidence):

| Chart value | Env var | Purpose |
|---|---|---|
| `validation.runnerImage` | `VALIDATION_RUNNER_IMAGE` | Slim runner image (uploader sidecar + inline-script runtime). CI publishes it as `<image.repository>-runner`. |
| `validation.ingestBaseUrl` | `VALIDATION_INGEST_BASE_URL` | Foyre base URL reachable from inside the validation environment (in vcluster shared mode, the in-cluster Service DNS). |
| `validation.allowInlineScripts` | `VALIDATION_ALLOW_INLINE_SCRIPTS` | Allow `custom.script` (default true). |

**Kubernetes ≥ 1.29** is required for the uploader sidecar (it uses native
sidecar containers). The sidecar uploads on pod termination within the
pod's grace period.

## Security considerations

- Foyre never stores Kubernetes Secret values from the validation
  environment — only names/metadata.
- Kubeconfigs are encrypted at rest and never exposed in logs, UI,
  artifacts, or API responses.
- Custom jobs/scripts are guardrailed by construction: Foyre builds the pod
  spec, so `privileged`, `hostPath`, `hostNetwork`, and `hostPID` are never
  set; the service-account token is not mounted; Linux capabilities are
  dropped; and resource limits are applied. Admins supply only the
  image/script, command, args, and env.
- Only admins can author pipelines, so only admin-approved images and
  scripts run.
- **Caveat:** a custom step that reads cluster Secrets and writes them to
  `/foyre/output` or stdout will have that output stored as an artifact.
  Artifacts follow the same access rules as the request; treat script and
  container output as operator responsibility. Disable inline scripts
  (`validation.allowInlineScripts: false`) for stricter environments.

## API

Everything here is also available via the API — see
[Validation Pipeline API](../api/validation-pipeline.md).

## Building your own steps

To add custom validation logic — either as a containerized
`custom.kubernetes_job` (no code) or as a native step type (code) — see
[Build Your Own Validation Step](../dev/build-a-validation-step.md).
