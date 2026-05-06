<p align="center">
  <img src="frontend/public/foyre-logo.png" alt="Foyre" width="96" />
</p>

<h1 align="center">Foyre</h1>

<p align="center">
  <strong>An internal front door for AI application requests.</strong><br />
  Intake, review, and validate new AI systems — with a real, isolated
  Kubernetes environment for each request.
</p>

<p align="center">
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

**Prerequisites**

- Python 3.11 or newer
- Node.js 18 or newer
- A Kubernetes cluster for validation environments — optional; you can run
  Foyre without one and skip validation.

### 1. Clone, install, and configure

```bash
git clone https://github.com/foyre/foyre.git
cd foyre
make install
make env
```

Open `backend/.env` and set `APP_SECRET_KEY` to a freshly-generated
Fernet key. This key encrypts kubeconfigs at rest; keep it somewhere safe.

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Seed the first admin

```bash
make seed
```

Creates an initial admin user with the credentials set in `backend/.env`
(defaults: `admin` / `admin`). Change these in `backend/.env` before seeding
in any shared environment.

### 3. Start the services

In two terminals:

```bash
make run       # backend on http://localhost:8000
make front     # frontend on http://localhost:5173
```

Open <http://localhost:5173> and sign in. You're set up for the intake +
review workflow without validation environments.

### 4. (Optional) Connect a host Kubernetes cluster

To enable per-request isolated validation environments:

1. Install the [`vcluster`](https://www.vcluster.com/docs/getting-started/setup)
   CLI on the machine running Foyre's backend.
2. Sign in to Foyre as an admin.
3. Go to **Administration → Validation environments**.
4. Follow the in-app **Setup guide** to create the service account and
   RBAC on your host cluster.
5. Paste the kubeconfig you minted, click **Test connection**, and save.

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

4. **Review.** Reviewers (and architects / admins) see all form answers,
   the risk assessment, any validation environment that's been
   provisioned, and a comment thread. They can move a request to
   `under_review`, post comments, and ultimately approve or reject.

5. **Decide.** An approval closes the request. A rejection records the
   reason and preserves the audit trail. The requester can tear down the
   validation cluster at any time, or an admin can do it on their behalf.

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

You can also install directly from a local clone:

```bash
git clone https://github.com/foyre/foyre.git
cd foyre

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

### Beyond the defaults

For **Postgres**, **Ingress / TLS**, supplying your own **Fernet / JWT**
secrets, multiple replicas, upgrades, and backups, use
[**DEPLOY.md**](./DEPLOY.md).

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

## Make targets

| Target              | Effect                                                           |
|---------------------|------------------------------------------------------------------|
| `make install`      | Create `backend/.venv` and install backend dependencies.         |
| `make env`          | Copy `backend/.env.example` to `backend/.env`.                   |
| `make seed`         | Create the database and the initial admin user (idempotent).    |
| `make run`          | Run the API on <http://localhost:8000> with auto-reload.        |
| `make reset`        | Delete the local SQLite database.                                |
| `make clean`        | `reset` plus remove `backend/.venv`.                             |
| `make front-install`| Install frontend dependencies.                                   |
| `make front`        | Run the Vite dev server.                                         |

Swagger UI is available at <http://localhost:8000/docs>.

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
