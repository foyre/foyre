# Validation Pipeline API

> Part of the [Foyre docs](../README.md).

All validation features are available over the JSON API, so pipelines can
be created and run without using the UI. Authenticate with a bearer token
(the same token the web UI uses).

```bash
BASE=http://localhost:8080
TOKEN=<your-bearer-token>
```

Authorization summary:

| Action | Allowed roles |
|---|---|
| Create/update/delete/set-default pipelines | `admin` |
| List/get pipelines, validate | `reviewer`, `architect`, `admin` |
| Run a pipeline | `reviewer`, `architect`, `admin` |
| View runs / artifacts / approval gate | anyone who can see the request |
| Get/update approval policy | `admin` |

## Pipeline management

### List pipelines

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/validation/pipelines
```

### Create a pipeline

The request body carries the YAML definition as a string field
(`definition_yaml`). For example, with a `pipeline.json` like:

```json
{
  "definition_yaml": "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: my-pipeline\nspec:\n  steps:\n    - name: inv\n      type: builtin.workload_inventory\n",
  "enabled": true,
  "is_default": false
}
```

```bash
curl -X POST $BASE/api/validation/pipelines \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @pipeline.json
```

### Get / update / delete a pipeline

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/validation/pipelines/<PIPELINE_ID>

curl -X PUT $BASE/api/validation/pipelines/<PIPELINE_ID> \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"enabled": false}'

curl -X DELETE $BASE/api/validation/pipelines/<PIPELINE_ID> \
  -H "Authorization: Bearer $TOKEN"
```

### Validate a definition (without saving)

Always returns `200` with `{ "valid": bool, "normalized": {...}|null, "error": str|null }`.

```bash
curl -X POST $BASE/api/validation/pipelines/validate \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"definition_yaml": "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: x\nspec:\n  steps:\n    - name: inv\n      type: builtin.workload_inventory\n"}'
```

### Set the default pipeline

```bash
curl -X POST $BASE/api/validation/pipelines/<PIPELINE_ID>/set-default \
  -H "Authorization: Bearer $TOKEN"
```

## Validation runs

### Start a validation run

`pipeline_id` is optional; omit it to use the default pipeline. The request
must have a **ready** validation environment.

```bash
curl -X POST $BASE/api/requests/<REQUEST_ID>/validation-runs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pipeline_id": "<PIPELINE_ID>", "reason": "Pre-production validation"}'
```

Returns `202` with the created run (status `queued`); it executes in the
background.

### List runs for a request

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/requests/<REQUEST_ID>/validation-runs
```

### Fetch a run (with step results)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/validation-runs/<RUN_ID>
```

Poll this until `status` is terminal (`passed`, `warning`, `failed`,
`error`, or `cancelled`).

## Artifacts (evidence)

### List a run's artifacts

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/validation-runs/<RUN_ID>/artifacts
```

### Download an artifact

Returns the raw bytes (not JSON), with a `Content-Disposition` attachment
header.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/validation-artifacts/<ARTIFACT_ID>/download \
  -o evidence.json
```

## Approval gate

### Check whether a request can be approved

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/requests/<REQUEST_ID>/validation-approval
```

Returns:

```json
{
  "blocked": true,
  "impact": "blocked",
  "reason": "The latest validation run has blocking failures. ...",
  "override_allowed": true,
  "missing_validation": false,
  "latest_run_id": 42
}
```

### Approve (with optional override)

Approval uses the existing status endpoint. To override a blocked gate,
set `override_validation: true` and supply `override_reason` (required when
overriding; recorded in request history).

```bash
# Normal approval (allowed only if the gate isn't blocking)
curl -X POST $BASE/api/requests/<REQUEST_ID>/status \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"new_status": "approved"}'

# Override a blocked approval
curl -X POST $BASE/api/requests/<REQUEST_ID>/status \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"new_status": "approved", "override_validation": true, "override_reason": "Risk accepted by security lead."}'
```

A blocked approval without override returns `409` with
`{ "detail": { "message": ..., "approval_impact": ..., "override_allowed": ... } }`.

## Approval policy (admin)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  $BASE/api/admin/validation/policy

curl -X PUT $BASE/api/admin/validation/policy \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"require_validation_before_approval": true}'
```

## Related

- [Docs index](../README.md)
- [Validation Pipelines Overview](../concepts/validation-pipelines.md)
- [Run a Validation Pipeline Against an AI Workload](../tutorials/run-validation-pipeline.md)
- [Configure Validation Pipelines](../admin/configure-validation-pipelines.md)
