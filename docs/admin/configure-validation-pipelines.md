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

### `custom.kubernetes_job`

Runs your own container image as a Kubernetes Job inside the validation
environment.

```yaml
- name: custom-company-check
  type: custom.kubernetes_job
  displayName: Company Policy Check
  required: false
  failurePolicy: warn
  dependsOn: [workload-inventory]
  timeoutSeconds: 300
  config:
    image: registry.example.com/security/company-ai-checker:latest
    command: ["/app/check"]
    args: ["--input", "/foyre/input/workload-inventory.json"]
    # env: { KEY: value }
```

**Contract for the custom container:**

- Input artifacts (e.g. `workload-inventory.json`) are mounted read-only at
  `/foyre/input`.
- A scratch volume is mounted at `/foyre/output`.
- The container **must print its normalized result as a single JSON object
  to stdout**:

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

Foyre reads the pod logs, extracts the last JSON object, and stores both
the parsed result and the raw logs as artifacts.

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

## Security considerations

- Foyre never stores Kubernetes Secret values from the validation
  environment — only names/metadata.
- Kubeconfigs are encrypted at rest and never exposed in logs, UI,
  artifacts, or API responses.
- Custom jobs are guardrailed by construction: Foyre builds the pod spec,
  so `privileged`, `hostPath`, `hostNetwork`, and `hostPID` are never set;
  the service-account token is not mounted; Linux capabilities are dropped;
  and resource limits are applied. Admins supply only the image, command,
  args, and env.
- Only admins can author pipelines, so only admin-approved images run as
  custom jobs.

## API

Everything here is also available via the API — see
[Validation Pipeline API](../api/validation-pipeline.md).
