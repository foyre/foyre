# Changelog

All notable changes to Foyre will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Validation pipelines.** Foyre can now run repeatable, declarative
  validation checks against the workload deployed in a request's
  validation environment, turning the vcluster into an evidence-producing
  review step. Admins author pipelines as YAML under **Admin → Validation
  pipelines**; a default pipeline ("Default AI Workload Validation") is
  seeded on install. Reviewers run a pipeline against a request from the
  request page. Built-in step types: `builtin.workload_inventory` (no
  secret values), `builtin.kubernetes_security` (posture findings), and
  `builtin.image_scan` (Trivy bundled by default, scanner interface is
  pluggable). `custom.kubernetes_job` runs an admin-provided container as a
  hardened Job inside the validation vcluster and ingests its normalized
  JSON result. Step results + downloadable evidence artifacts attach to the
  request. A configurable approval gate (`requireValidationBeforeApproval`,
  `blockApprovalOnFailedValidation`, `allowValidationOverride`) can warn or
  block approval; blocked approvals can be overridden with a recorded
  reason. Full API parity (pipeline CRUD, runs, artifacts, policy). See
  [docs/concepts/validation-pipelines.md](docs/concepts/validation-pipelines.md).
- **Configurable intake form.** Admins can now customize the request form
  from a new **Admin → Intake form** tab: relabel and re-section built-in
  fields, add custom fields (text, long text, dropdown, yes/no), reorder
  sections, and reset back to the built-in default. A live preview pane
  shows requesters' view side-by-side. Built-in fields backing the risk
  engine are locked so they can be relabeled but not removed or retyped,
  keeping risk evaluation stable across customizations. Custom required
  fields are enforced at submit time and surfaced in the request detail
  view alongside the built-in ones.

### Security
- **Chart 0.2.4:** the seed Secret is now a `pre-install,pre-upgrade`
  hook (was `pre-install` only). Without this, a `helm upgrade` with a
  fresh `--set-string seed.admin.password=...` would silently keep the
  original install's password, and combined with the new
  insecure-defaults guard would fail the post-upgrade seed Job. Operators
  can now rotate the seed password by re-running `helm upgrade`.
- **Chart 0.2.3:** `helm install` now fails template-rendering if
  `seed.admin.password` is left as the `CHANGE_ME_ON_FIRST_INSTALL`
  placeholder or empty. Prevents accidental deploys with a guessable admin
  password.
- The seeded admin user is now created with `must_change_password: true`,
  so the operator-supplied seed password is one-time-use even if it leaks.
- **Backend:** when `APP_ENV` is not `local`/`dev`/`test`, the app refuses
  to boot if `JWT_SECRET` is a known-insecure default; the one-shot seed
  Job refuses to run if `SEED_ADMIN_PASSWORD` is a known-insecure default.
  Local dev still warns but boots. The seed Job runs with
  `APP_ENV=production` so it inherits this protection.
- **Provisioning:** vcluster CLI errors are now logged in full and the
  user-facing error includes up to 4 KB (was 500 chars), so failures like
  multi-line RBAC errors are debuggable from pod logs alone.
- **Host-cluster setup guide (in-app and README):** added `escalate` /
  `bind` verbs to the recommended RBAC so vcluster's ClusterRole +
  ClusterRoleBinding can actually be created. Added a one-shell-command
  kubeconfig generator that reads the API server URL + CA from the
  operator's current kubectl context (no hand-edited YAML).

## [0.1.0] - 2026-05-07

First usable release. Foyre is an internal front door for AI application
requests: structured intake, deterministic risk classification, role-aware
review workflow, and per-request isolated Kubernetes virtual clusters
(via vcluster) for hands-on validation before approval.

### Added

#### Application
- Structured intake form for AI deployment requests with conditional
  fields, client-side validation, and draft / submit flow.
- Deterministic risk classification (low / medium / high / unknown) with
  human-readable reasons; rules live in `services/risk_service.py`.
- Workflow lifecycle: `draft → submitted → ready_for_review →
  under_review → approved | rejected`, enforced by a single transition
  table in `services/workflow_service.py`.
- Reviewer comments and an append-only history of lifecycle events
  (creation, edits, submissions, status changes, comments, validation
  environment events).
- Local username / password authentication with bcrypt hashing, JWT
  access tokens, and forced password rotation for temporary accounts.
- Pluggable authentication-provider interface — local provider only
  today; LDAP / AD / OIDC slots reserved.
- Role model: `requester`, `reviewer`, `architect`, `admin`. Admin can
  act on behalf of other users, recorded in the audit trail.
- Per-request validation environments via
  [vcluster](https://www.vcluster.com): isolated virtual clusters
  provisioned on a host Kubernetes cluster, with scoped kubeconfigs
  delivered to the requester through a once-shown download callout.
- Admin-managed host cluster configurations with kubeconfig encryption
  at rest (Fernet), in-app setup guide, and pre-save connection tests.
- Web UI: requests list with status filter pills and free-text search,
  request detail with role-aware actions, account page, and an admin
  section with horizontal tabs for Users and Validation environments.
- Foyre branding (logo, favicon, login page, navbar).

#### Database backends
- SQLite default (single replica, on a chart-managed PVC).
- Embedded Postgres via the upstream Bitnami subchart
  (`postgresql.enabled=true`).
- External Postgres with inline credentials
  (`database.postgres.host=...`).
- External Postgres with bring-your-own Secret
  (`database.existingSecret=...`).
- `psycopg[binary]` bundled in the runtime image so Postgres works out
  of the box; SQLAlchemy `pool_pre_ping` for long-lived Postgres
  connections.

#### Deployment / Helm chart
- Helm chart at `deploy/helm/foyre`, published from
  [github.com/foyre/foyre](https://github.com/foyre/foyre) to
  `https://foyre.github.io/foyre/`.
- Chart-managed Secrets for `APP_SECRET_KEY` (Fernet) and `JWT_SECRET`,
  generated on first install with `helm.sh/resource-policy: keep`.
- Idempotent post-install seed Job that creates the initial admin user.
- Optional Ingress, configurable Service type (defaults to `NodePort`
  for ease of bring-up), and override-anything values.
- Quickstart script `scripts/quickstart-k3s.sh` that bootstraps k3s and
  installs Foyre on a fresh Ubuntu VM.

#### CI/CD
- GitHub Actions: CI workflow (frontend build, **pytest**, Python
  compile, Helm lint) and a container workflow that builds multi-arch
  images on pull requests (no push) and publishes
  `zfeldstein/foyre` from pushes and tags.
- Optional **Helm install + smoke + teardown** on a self-hosted runner
  when `FOYRE_K8S_INTEGRATION` is enabled.
- Optional **persistent Helm deploy** per branch (`FOYRE_AUTO_DEPLOY`)
  with SHA-pinned image and post-rollout verification.
- **Cleanup of feature namespaces** when a PR merges into `main`
  (`cleanup-feature-namespace.yml`); shared
  `scripts/ci/k8s-deploy-namespace.sh` for namespace naming.
- Backend dev dependencies (`requirements-dev.txt`) and initial pytest
  suite for risk and workflow services, plus `/healthz` regression
  test.
- Release automation script (`scripts/release.sh`) that handles tag,
  changelog, image, and Helm chart publishing in one go.

### Changed
- Licensed under the [Apache License, Version 2.0](./LICENSE) (initially
  drafted under BSL 1.1).

[Unreleased]: https://github.com/foyre/foyre/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/foyre/foyre/releases/tag/v0.1.0
