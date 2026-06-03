<p align="center">
  <a href="https://foyre.ai">
    <img src="frontend/public/foyre-logo.png" alt="Foyre" width="96" />
  </a>
</p>

<h1 align="center">Foyre</h1>

<p align="center">
  <strong>An internal front door for AI application requests.</strong><br />
  Intake, review, and validate new AI systems — with a real, isolated
  Kubernetes environment for each request.
</p>

<p align="center">
  <a href="https://foyre.ai"><strong>foyre.ai</strong></a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#deployment">Deployment</a> ·
  <a href="#contributing">Contributing</a> ·
  <a href="#license">License</a>
</p>

---

Every organization running AI workloads eventually faces the same chaos: one
team wants to ship a chatbot, another wants to deploy a RAG service, a third
is experimenting with agents — and IT, platform, and security keep getting
surprised by the details after the request has been committed. Foyre turns
that chaos into a repeatable, auditable workflow.

Requesters fill out a structured intake form. The system classifies the
risk. Reviewers get a real, running Kubernetes virtual cluster for each
request — so they can inspect what's actually being deployed, not just read
about it. Decisions and discussions are recorded against every request.

> Learn more about the product, see screenshots, and read the design
> background at **[foyre.ai](https://foyre.ai)**.

## Features

- **Structured intake form** that captures the information platform,
  security, and architecture teams actually need: workload type, data
  classification, external model APIs, vector databases, agent behaviors,
  GPU and egress requirements.
- **Isolated validation environments.** Requesters can provision a real,
  per-request Kubernetes virtual cluster via
  [vcluster](https://www.vcluster.com). They receive a scoped kubeconfig,
  deploy their application, then flag the request as ready for review.
  Reviewers see a living deployment, not a questionnaire.
- **Validation pipelines.** Run repeatable, declarative checks against the
  workload deployed in a validation environment — workload inventory,
  Kubernetes security posture, container image scanning (Trivy by default,
  pluggable), and your own custom containerized checks. Results and
  evidence artifacts attach to the request, and a configurable gate can
  warn or block approval. See
  [Validation Pipelines](docs/concepts/validation-pipelines.md).
- **Deterministic risk classification** — every submitted request gets a
  low / medium / high / unknown rating, with human-readable reasons. Rules
  are plain Python and easy to extend.
- **Role-aware workflow.** `requester`, `reviewer`, `architect`, and
  `admin` roles with a small, auditable status machine (`draft →
  submitted → ready_for_review → under_review → approved | rejected`).
- **Built-in audit trail.** Reviewer comments, status transitions,
  risk evaluations, and validation-environment lifecycle events are
  recorded against every request, attributed to the acting user.
- **Self-hosted and secure by default.** Local username/password auth
  with bcrypt hashing, forced password rotation for temporary accounts,
  encrypted kubeconfigs at rest. Pluggable seams for LDAP / AD / OIDC.
- **Lightweight stack.** FastAPI + SQLAlchemy + SQLite out of the box
  (Postgres-ready), React + TypeScript + Vite for the UI.

## Who it's for

Platform, IT, and security teams at organizations where product teams want
to ship AI features faster than internal review processes can keep up with.
Foyre gives those teams a standard process — without another heavyweight
ITSM tool — and gives reviewers a way to verify what's being asked for.

## Quick start

The fastest path is Helm on Kubernetes. Foyre runs as a single container with
the React UI baked in, so you do not need to run a separate frontend process.

### Option 1: Install With Helm

Prerequisites:

- Kubernetes cluster with a default StorageClass
- `helm` 3.10+
- `kubectl` configured for the cluster

```bash
helm repo add foyre https://foyre.github.io/foyre/
helm repo update

helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

Open the Web UI using the NodePort service:

```bash
kubectl --namespace foyre get svc foyre
kubectl get nodes -o wide
```

Look for a service port like `80:31234/TCP`, then open:

```text
http://<node-ip>:31234/
```

Sign in as `admin` with the password you set in `seed.admin.password`, then
change it from the user menu.

For local/private access instead of NodePort:

```bash
kubectl --namespace foyre port-forward svc/foyre 8080:80
```

Then open <http://localhost:8080>.

### Option 2: Fresh Ubuntu VM / Lab Install

If you do not already have Kubernetes, use the quickstart script on a fresh
Ubuntu VM. It installs single-node **k3s**, installs Helm if needed, installs
Foyre, and prints the Web UI URL and generated admin password.

```bash
curl -fsSL https://raw.githubusercontent.com/foyre/foyre/main/scripts/quickstart-k3s.sh | bash
```

To choose your own admin password:

```bash
curl -fsSL https://raw.githubusercontent.com/foyre/foyre/main/scripts/quickstart-k3s.sh \
  | SEED_ADMIN_PASSWORD='change-me-on-first-login' bash -s
```

### Connect A Host Kubernetes Cluster

Foyre works without validation environments, but the Kubernetes validation
workflow needs a host cluster configuration:

1. Sign in to Foyre as an admin.
2. Go to **Administration → Validation environments**.
3. Follow the in-app **Setup guide** to create the service account and
   RBAC on your host cluster.
4. Paste the kubeconfig you minted, click **Test connection**, and save.

Once saved, requesters will see a **Create isolated cluster** button on
their submitted requests.

## How it works

```
┌──────────┐  submit  ┌───────────┐  deploy  ┌─────────────────┐  review  ┌─────────────┐
│Requester │ ───────▶ │ Intake    │ ───────▶ │ Validation      │ ───────▶ │ Decision    │
│          │          │ form      │          │ environment     │          │             │
│          │          │ (risk     │          │ (vcluster +     │          │ approved /  │
│          │          │  scored)  │          │  kubeconfig)    │          │  rejected   │
└──────────┘          └───────────┘          └─────────────────┘          └─────────────┘
```

1. **Submit.** A requester opens Foyre, fills in the intake form, and
   submits. The form asks about workload type, data classification, use of
   external model APIs, vector databases, agent behaviors, GPU needs, and
   internet egress. Fields are conditionally revealed — the form doesn't
   ask about a vector database if none is involved.

2. **Auto-classify.** On submit, Foyre applies a small set of deterministic
   rules to rate the request (e.g. *external model API + regulated data →
   high*; *agent takes actions on behalf of a user → high*). The request
   status becomes `submitted` and the risk rating is attached along with
   human-readable reasons.

3. **Validate.** Optionally, the requester clicks **Create isolated
   cluster**. Foyre provisions a new vcluster on the connected host,
   patches its Kubernetes Service to a NodePort, and returns a scoped
   kubeconfig — shown once, downloadable as a YAML file. The requester
   uses `kubectl` / `helm` to deploy their application into the cluster,
   then flags the request as **ready for review**.

4. **Run validation pipelines.** Reviewers run a declarative validation
   pipeline against the deployed workload: it collects a workload
   inventory, reviews Kubernetes security posture, scans container images,
   and can run custom containerized checks. Results and downloadable
   evidence attach to the request, and the run's approval impact (`none`,
   `warning`, or `blocked`) feeds the decision below. See
   [Validation Pipelines](docs/concepts/validation-pipelines.md).

5. **Review.** Reviewers (and architects / admins) see all form answers,
   the risk assessment, any validation environment that's been
   provisioned, validation results, and a comment thread. They can move a
   request to `under_review`, post comments, and ultimately approve or
   reject.

6. **Decide.** An approval closes the request — blocked by validation
   policy unless the findings are resolved or a reviewer overrides with a
   recorded reason. A rejection records the reason and preserves the audit
   trail. The requester can tear down the validation cluster at any time,
   or an admin can do it on their behalf.

Every status transition, comment, provisioning event, and teardown is
recorded against the request with the acting user. Admins can act on
behalf of other users to unblock stuck workflows; in those cases the
acting admin is the one recorded in the audit log.

## User roles

| Role        | What they can do                                                       |
|-------------|-----------------------------------------------------------------------|
| `requester` | Create, edit, and submit their own requests; provision validation environments; mark requests ready for review. |
| `reviewer`  | See all requests; move submitted requests through review; post comments; approve or reject. |
| `architect` | Same as `reviewer` today; reserved for future differentiation (e.g. architecture-specific sign-off). |
| `admin`     | All of the above, plus manage users, configure host clusters, and provision on behalf of requesters when needed. |

Role descriptions and capabilities are surfaced in the UI. User management
and validation-environment configuration live under **Administration**;
personal settings (password change, account info) live in the user menu.

## Architecture

Foyre is two small applications talking over a JSON API.

```
backend/     FastAPI + SQLAlchemy + SQLite (Postgres-ready via DATABASE_URL)
frontend/    React + TypeScript + Vite
```

**Backend layout**

```
backend/app/
  api/               HTTP routes (auth, requests, comments, users,
                     validation_environments, admin/users, admin/host_clusters)
  auth/              local password auth, JWT tokens, pluggable provider
                     interface for LDAP/AD/OIDC
  domain/            enums and the canonical intake-form schema
  models/            SQLAlchemy models
  provisioning/      vcluster provider, kube client, encryption helpers
  repositories/      thin DB access layer
  schemas/           Pydantic request / response DTOs
  services/          request workflow, risk rules, comments, history
```

**Key design invariants**

- All status transitions go through `services/workflow_service.py`. Its
  allow-list is the single source of truth for status rules.
- The risk classifier is a pure function in `services/risk_service.py` —
  no DSL, no rule engine; rules are plain Python if-statements with a
  human-readable reason string each.
- Validation environments are provisioned on a host cluster you own.
  Foyre never runs your application workloads itself.
- Sensitive credentials — the host cluster's kubeconfig and each
  requester's vcluster kubeconfig — are encrypted at rest with
  `APP_SECRET_KEY` (Fernet).
- Authentication providers are swappable. Only `local` is implemented
  today; LDAP/AD/OIDC are clean seams.

## Deployment

Foyre ships as one container image plus a Helm chart. **Source code** lives at
[github.com/foyre/foyre](https://github.com/foyre/foyre); the chart defaults to
pulling the **[Docker Hub `zfeldstein/foyre`](https://hub.docker.com/r/zfeldstein/foyre)**
image.

### Prerequisites (Helm)

- Kubernetes **1.27+** (tested through 1.30).
- [**Helm 3.10+**](https://helm.sh/docs/intro/install/) and **`kubectl`**
  configured for your cluster.
- A **default StorageClass** (the chart requests a PVC for SQLite unless you
  switch to Postgres). See [DEPLOY.md](./DEPLOY.md) if your cluster has none.

### Helm Install

If you are installing from the published Helm repo:

```bash
helm repo add foyre https://foyre.github.io/foyre/
helm repo update

helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

For a specific chart version:

```bash
helm upgrade --install foyre foyre/foyre \
  --version 0.1.0 \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

You can also install directly from a local clone. The chart has an optional
PostgreSQL subchart, so run `helm dependency update` once before installing
(or whenever `Chart.yaml` changes):

```bash
git clone https://github.com/foyre/foyre.git
cd foyre

helm dependency update deploy/helm/foyre

helm upgrade --install foyre deploy/helm/foyre \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

That command:

- Creates namespace `foyre` (if needed) and release **`foyre`**.
- Deploys the app **Deployment**, **Service** (`NodePort`, name **`foyre`**
  when the release name is `foyre`), optional **Ingress** (off by default),
  and a **PVC** for SQLite at `/data`.
- Runs a **post-install seed Job** that creates the initial admin if missing.
- Waits for resources to become ready (`--wait`).

**Set a strong seed password** before any shared or production cluster. You
can also override the admin username and email; see
[`deploy/helm/foyre/values.yaml`](./deploy/helm/foyre/values.yaml) under `seed`.

**Pin the image tag** if you want a specific application image:

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set image.tag=0.1.0 \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

Use `latest`, a **semver tag** from a release, or a **branch / `sha-*` tag**
published by CI (see [CONTRIBUTING.md](./CONTRIBUTING.md)).

**Use a different registry or repository** only if you are not pulling from
Docker Hub:

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set image.repository=my.registry.example/foyre \
  --set image.tag=1.2.3 \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

Add `--set imagePullSecrets[0].name=...` if the cluster needs credentials to
pull the image.

### Open The Web UI

The chart defaults to a **NodePort** service, which is convenient for a lab or
single-node cluster:

```bash
kubectl --namespace foyre get svc foyre
```

Look for the `PORT(S)` value, for example `80:31234/TCP`. Open:

```text
http://<node-ip>:31234/
```

If you do not know the node IP:

```bash
kubectl get nodes -o wide
```

Use the `INTERNAL-IP` or `EXTERNAL-IP` that is reachable from your browser.

For local/private access without exposing a NodePort, use port-forwarding:

```bash
kubectl --namespace foyre port-forward svc/foyre 8080:80
```

Then open <http://localhost:8080> and sign in as **`admin`** with the password
you passed in `seed.admin.password`. Change it immediately under your account
menu.

For a production-style install, use Ingress and set the service back to
`ClusterIP`:

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set service.type=ClusterIP \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=foyre.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

Then point DNS for `foyre.example.com` at your Ingress controller. For TLS,
add `ingress.tls` and cert-manager annotations in a values file rather than a
long `--set` command.

### Database backends

Foyre supports four database configurations. The chart picks one based on
**what you set in values**, not a `type` flag. The selection order, first
match wins, is:

| Priority | If this is set in values | Foyre uses |
|---:|---|---|
| 1 | `database.existingSecret` | the DATABASE_URL stored in that Secret (BYO) |
| 2 | `database.url` | that URL exactly, as-is |
| 3 | `postgresql.enabled: true` | **Embedded Postgres** (Bitnami subchart) |
| 4 | `database.postgres.host` | **External Postgres** at that host |
| 5 | (nothing) | **SQLite** at `/data/foyre.db` on a chart-managed PVC |

When any Postgres mode wins, the chart automatically **skips the SQLite PVC**
and the `/data` mount.

The Foyre release name in every example below is `foyre`. Change `--namespace`
or release name as you wish; the Postgres StatefulSet in the embedded mode is
named `<release>-postgresql`.

#### Mode 1: SQLite (default)

Single replica, single SQLite file on a PVC. Ideal for evaluation, demos,
small teams, and the [k3s quickstart](#option-2-fresh-ubuntu-vm--lab-install).

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

What you get:
- A 5 GiB PVC named `<release>-data` (`helm.sh/resource-policy: keep`).
- `DATABASE_URL=sqlite:////data/foyre.db` injected from a chart-managed Secret.

Customize the SQLite location or PVC size in `values.yaml`:

```yaml
persistence:
  size: 20Gi
database:
  sqlite:
    path: /data/foyre.db   # mounted at persistence.mountPath
```

Constraints:
- **Single replica only.** Two pods opening the same SQLite file corrupts it.
  The chart sets `replicaCount: 1` and `strategy.type: Recreate`.
- Backups = snapshot the PVC, or stop the pod and copy `foyre.db`.

#### Mode 2: Embedded Postgres (bundled with Foyre)

The chart deploys a real Postgres for you using the
[upstream Bitnami chart](https://artifacthub.io/packages/helm/bitnami/postgresql)
as a subchart, and wires Foyre to it. Good for lab installs and
self-contained deployments where you do not want to run Postgres yourself.

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set postgresql.enabled=true \
  --set postgresql.auth.password='strong-postgres-password' \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

What you get:
- A `StatefulSet` named **`foyre-postgresql`** with its own PVC.
- A `Service` named **`foyre-postgresql`** at port `5432`.
- `DATABASE_URL=postgresql+psycopg://foyre:<password>@foyre-postgresql:5432/foyre`
  injected into Foyre.

Defaults the chart sets for the Bitnami subchart:

```yaml
postgresql:
  enabled: true
  auth:
    username: foyre        # the application user (not "postgres")
    database: foyre
    password: ""           # required; set --set postgresql.auth.password=...
  primary:
    persistence:
      enabled: true
      size: 8Gi
```

Override **any** Bitnami value under the `postgresql.*` key — image,
resources, persistence, init scripts, etc. See the chart's
[full values reference](https://artifacthub.io/packages/helm/bitnami/postgresql).

Examples:

```yaml
postgresql:
  enabled: true
  auth:
    username: foyre
    database: foyre
    password: strong-postgres-password
  primary:
    persistence:
      size: 20Gi
      storageClass: fast-ssd
    resources:
      requests:
        cpu: 250m
        memory: 512Mi
```

Notes:
- The Postgres pod takes ~30–90 seconds to be ready on first install. The
  Foyre pod will crash-restart once or twice waiting for it; use
  `--wait --timeout 10m` so Helm reports success after both come up.
- The Bitnami chart auto-generates a `postgres` admin password and stores it
  in `Secret/<release>-postgresql`. Foyre does not use that account; it
  connects as `foyre` (or whatever you set in `postgresql.auth.username`).

#### Mode 3: External Postgres (inline credentials)

Point Foyre at a Postgres you already run — managed (RDS, Cloud SQL, Aiven,
Neon, Supabase) or self-hosted. The trigger is **`database.postgres.host`**.

```bash
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set database.postgres.host=db.internal \
  --set database.postgres.port=5432 \
  --set database.postgres.database=foyre \
  --set database.postgres.user=foyre \
  --set database.postgres.password='change-me' \
  --set database.postgres.sslmode=require \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

What happens:
- The chart writes `Secret/<release>-db` containing `DATABASE_URL=...`.
- Foyre reads it and connects to your Postgres.
- No SQLite PVC, no embedded Postgres pod.

The `sslmode` field is optional but recommended for managed Postgres
(`require`, `verify-ca`, or `verify-full`).

This mode keeps the password in Helm values — fine for self-hosted clusters
where the values file is treated as sensitive. For stricter setups, see Mode 4.

#### Mode 4: External Postgres with bring-your-own Secret (production)

The chart never sees your Postgres credentials. Recommended for managed
Postgres, Vault, Sealed Secrets, External Secrets Operator, etc.

```bash
# 1. Create a Secret containing the full DATABASE_URL.
kubectl -n foyre create secret generic foyre-db \
  --from-literal=DATABASE_URL='postgresql+psycopg://foyre:...@db.internal:5432/foyre?sslmode=require'

# 2. Tell Helm to read it.
helm upgrade --install foyre foyre/foyre \
  --namespace foyre --create-namespace \
  --set database.existingSecret=foyre-db \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

The Secret key defaults to `DATABASE_URL`; override with
`database.existingSecretKey` if your tool emits a different key.

#### Verifying the active backend

After install:

```bash
# Helm's NOTES.txt prints the resolved backend
helm -n foyre get notes foyre

# Or read the URL the app is actually using (chart-managed mode)
kubectl -n foyre get secret foyre-db -o jsonpath='{.data.DATABASE_URL}' | base64 -d ; echo

# Embedded mode: confirm the Postgres pod is up
kubectl -n foyre get pods -l app.kubernetes.io/name=postgresql
kubectl -n foyre exec sts/foyre-postgresql -- pg_isready -U foyre
```

#### Switching modes after install

Foyre **does not migrate data** between backends automatically. Switching
backends starts with a fresh database, which means re-seeding the admin and
losing existing requests / comments / history. To preserve data, dump from
the old backend and restore into the new one before switching:

```bash
# Example: SQLite -> Postgres
kubectl -n foyre exec deploy/foyre -- sqlite3 /data/foyre.db .dump > foyre.sql
# Restore into your Postgres (manual table mapping may be required).
```

If you only need to swap embedded → external Postgres or rotate
credentials, the simpler path is `helm upgrade` with the new values; the
seed Job is idempotent and your existing rows are preserved on the same
Postgres.

For Ingress + TLS, multiple replicas, secret rotation, upgrades, and
backups, see [DEPLOY.md](./DEPLOY.md).

### Beyond the defaults

For **Ingress / TLS**, **secret rotation**, **multiple replicas**, **upgrades**,
and **backups**, use [**DEPLOY.md**](./DEPLOY.md).

### Build the image locally

If you are not pulling from a registry:

```bash
docker build -t foyre:dev .
```

Point Helm at it with `--set image.repository=...` and `--set image.tag=...`,
or load the image into **kind** / **minikube** and set `imagePullPolicy` to
`Never` / `IfNotPresent` as appropriate.

### CI-built images and cluster deploy

When [Docker Hub](https://hub.docker.com/r/zfeldstein/foyre) credentials are
configured, **pushes** (and **`workflow_dispatch`**) run **validate → publish →
Deploy (Helm)** in [`.github/workflows/container.yml`](./.github/workflows/container.yml):
pytest and helm lint gate the image build; the image is pushed with tags such as
**`sha-<short>`**, **`main`**, **`latest`** (on `main` only), and semver tags for
**`v*`** git tags. The **Deploy** job runs on your **self-hosted** runner (default
**`runs-on: ["self-hosted"]`**) and runs **`helm upgrade --install`** with
**`--set image.tag=<sha>`** and **`service.type=NodePort`**, then prints the
**NodePort** in the job log for manual checks (`http://<node-ip>:<port>/`).

Set repository variable **`FOYRE_AUTO_DEPLOY=false`** to skip cluster deploy and
the merge-time namespace cleanup workflow.

Optional: **`FOYRE_K8S_INTEGRATION=true`** enables an ephemeral Helm smoke install
in `foyre-ci-<run_id>`. **Pull requests** still run [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)
for tests plus a non-pushing Docker build in the container workflow.

**pytest** runs in CI on PRs and in **validate** on every push before publish.

### Environment variables (reference)

Inside the container the chart wires (or you override) the usual settings:

| Variable             | Purpose                                                           |
|----------------------|-------------------------------------------------------------------|
| `APP_SECRET_KEY`     | Fernet key for encrypting kubeconfigs at rest. Generated by the Helm chart on first install. |
| `JWT_SECRET`         | Secret for signing access tokens. Generated by the Helm chart on first install. |
| `DATABASE_URL`       | SQLAlchemy URL. Defaults to SQLite at `/data/foyre.db` in the container; override for Postgres. |
| `SEED_ADMIN_*`       | Initial admin credentials. Provided to the seed Job by the chart. |

## Local Development

The README is optimized for installing and running Foyre. For local Python /
Node development commands, tests, and contribution workflow, see
[CONTRIBUTING.md](./CONTRIBUTING.md).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) for
development setup, coding standards, and the sign-off policy. All
interactions are governed by our
[Code of Conduct](./CODE_OF_CONDUCT.md).

## Security

If you've found a security issue, please **do not** open a public issue.
See [SECURITY.md](./SECURITY.md) for how to report it privately.

## License

Foyre is licensed under the [Apache License, Version 2.0](./LICENSE).

You may use, modify, and distribute Foyre — including in commercial
products — subject to the terms of the license. See the [LICENSE](./LICENSE)
and [NOTICE](./NOTICE) files for the full text and attribution requirements.

Copyright (c) 2026 Zachary Feldstein and contributors.

## Documentation

In-repo guides under [`docs/`](docs/):

- [Validation Pipelines Overview](docs/concepts/validation-pipelines.md) — what they are and why.
- [Run a Validation Pipeline Against an AI Workload](docs/tutorials/run-validation-pipeline.md) — hands-on tutorial.
- [Configure Validation Pipelines](docs/admin/configure-validation-pipelines.md) — admin guide + YAML reference.
- [Build Your Own Validation Step](docs/dev/build-a-validation-step.md) — extend pipelines with custom or native steps.
- [Validation Pipeline API](docs/api/validation-pipeline.md) — API reference with curl examples.

## Learn more

- [foyre.ai](https://foyre.ai) — product site, docs, and announcements
- [github.com/foyre/foyre](https://github.com/foyre/foyre) — source code, issues, and releases
- [Docker Hub](https://hub.docker.com/r/zfeldstein/foyre) — container images
