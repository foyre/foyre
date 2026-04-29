# Deploying Foyre

This guide walks through running Foyre on Kubernetes for real use.
For local development, see the
[main README](./README.md#quick-start).

## Architecture overview

Foyre ships as a single container image:

- **Backend** — FastAPI / uvicorn on port 8000.
- **Frontend** — Vite-built React SPA, baked into the image and served
  by the backend at the same origin.
- **CLIs** — the `vcluster` and `kubectl` binaries are included so the
  backend can shell out to provision validation environments on a
  host Kubernetes cluster.

Persistence is one of:

- **SQLite on a PVC** (default, simple). Single replica only.
- **Postgres** (recommended for shared deployments). External; the
  chart only needs `DATABASE_URL`.

The Helm chart is at [`deploy/helm/foyre`](./deploy/helm/foyre).

## Prerequisites

- A Kubernetes cluster (1.27+ tested against 1.30).
- `helm` 3.10+ and `kubectl` configured against your cluster.
- A container registry your cluster can pull from. Foyre's official
  image lives at `ghcr.io/foyre/foyre`. To build your own:

  ```bash
  docker build -t ghcr.io/your-org/foyre:0.1.0 .
  docker push    ghcr.io/your-org/foyre:0.1.0
  ```

- (Optional) an Ingress controller and cert-manager if you want
  TLS-terminated public access.
- (Optional) a host Kubernetes cluster for validation environments.
  Foyre never auto-discovers one — admins paste a kubeconfig in the
  UI after install.

## Install — quickest path

```bash
git clone https://github.com/foyre/foyre.git
cd foyre

helm upgrade --install foyre deploy/helm/foyre \
  --namespace foyre --create-namespace \
  --set seed.admin.password='change-me-on-first-login' \
  --wait
```

This installs Foyre with:

- 1 replica
- A 5 GiB PVC (default StorageClass) for SQLite at `/data`
- A `ClusterIP` Service named `foyre`
- An auto-generated `APP_SECRET_KEY` and `JWT_SECRET` stored in a
  Secret with `helm.sh/resource-policy=keep`
- A seed admin (`admin` / your password)

To reach the UI:

```bash
kubectl --namespace foyre port-forward svc/foyre 8080:80
# then open http://localhost:8080
```

Sign in as `admin` and rotate the seeded password immediately.

## Production install

For anything beyond a kick-the-tires evaluation:

1. Use **Postgres** instead of SQLite.
2. Provide your own **`APP_SECRET_KEY`** and **`JWT_SECRET`** via an
   existing Secret you back up.
3. Configure an **Ingress** with TLS.
4. Pin an explicit **image tag** rather than relying on the chart
   default.

Create a `values-prod.yaml` and fill in your specifics:

```yaml
# values-prod.yaml
image:
  repository: ghcr.io/foyre/foyre
  tag: "0.1.0"

replicaCount: 1   # See note below before changing this.

# --- Database --------------------------------------------------------
# Provision Postgres separately (managed RDS / Cloud SQL / Bitnami chart
# / etc.) and put the connection string in a Secret like:
#   kubectl -n foyre create secret generic foyre-db \
#     --from-literal=DATABASE_URL='postgresql+psycopg://foyre:...@db.internal:5432/foyre'
database:
  existingSecret: foyre-db
  existingSecretKey: DATABASE_URL

# --- Long-lived secrets ----------------------------------------------
# Pre-create with:
#   kubectl -n foyre create secret generic foyre-app \
#     --from-literal=APP_SECRET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
#     --from-literal=JWT_SECRET="$(openssl rand -hex 32)"
secrets:
  existingSecret: foyre-app

# --- Persistence -----------------------------------------------------
# Not strictly required when using Postgres, but harmless. Set
# enabled: false to skip the PVC entirely.
persistence:
  enabled: false

# --- Ingress + TLS ---------------------------------------------------
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: 10m
  hosts:
    - host: foyre.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: foyre-tls
      hosts:
        - foyre.example.com

# --- Seed admin ------------------------------------------------------
seed:
  enabled: true
  admin:
    username: admin
    email: admin@example.com
    # Change immediately after first login.
    password: "set-via-secret-or-rotate-immediately"

# --- Resources -------------------------------------------------------
resources:
  requests:
    cpu: 200m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

Install:

```bash
helm upgrade --install foyre deploy/helm/foyre \
  --namespace foyre --create-namespace \
  --values values-prod.yaml \
  --wait
```

## Multiple replicas

The chart defaults to a single replica because the default storage
backend (SQLite) cannot be safely opened by more than one process at
a time.

If — and only if — you have switched to Postgres, you can scale up:

```yaml
replicaCount: 3
persistence:
  enabled: false
```

Foyre's background provisioning thread for validation environments is
fine to run in multiple pods; each pod handles requests it received.

## Connecting a host cluster (validation environments)

This step is performed in the UI **after** Foyre is installed; the
chart does not configure host clusters. Sign in as admin and:

1. **Administration → Validation environments**.
2. Expand **Setup guide** for the exact `ServiceAccount` + RBAC
   commands to run on the host cluster.
3. Mint a kubeconfig for the service account, paste it into the form,
   click **Test connection**, and save.

Foyre stores the kubeconfig encrypted at rest (Fernet, using your
`APP_SECRET_KEY`).

## Backups

Two things to back up:

1. **The database.** With Postgres: your usual `pg_dump` / managed-DB
   snapshot strategy. With SQLite: snapshot the PVC at `/data/foyre.db`
   while the pod is briefly stopped, or copy it out with
   `kubectl exec foyre-0 -- sqlite3 /data/foyre.db .dump > backup.sql`.

2. **The `APP_SECRET_KEY`.** Without it, every kubeconfig persisted by
   Foyre — host kubeconfigs configured by admins, scoped vcluster
   kubeconfigs minted for requesters — becomes unreadable. Treat it
   like a master encryption key. The chart marks the auto-generated
   Secret with `helm.sh/resource-policy=keep` so a `helm uninstall`
   won't drop it, but you should still back it up:

   ```bash
   kubectl -n foyre get secret foyre-app -o yaml > foyre-app-secret-backup.yaml
   ```

## Upgrading

```bash
git pull
helm upgrade foyre deploy/helm/foyre \
  --namespace foyre \
  --values values-prod.yaml \
  --wait
```

The chart's seed Job runs as a `post-install,post-upgrade` hook and
is idempotent (it skips creating the admin if it already exists).

To upgrade to a specific image tag without changing the chart:

```bash
helm upgrade foyre deploy/helm/foyre \
  --namespace foyre \
  --reuse-values \
  --set image.tag=0.2.0
```

The Deployment uses a `Recreate` strategy, not `RollingUpdate`, to
avoid two pods writing to the same SQLite file during a rollout.
There will be a brief downtime window (single-digit seconds) during
upgrades.

## Uninstalling

```bash
helm uninstall foyre --namespace foyre
```

By design, the following resources **survive** uninstall (so an
accidental `helm uninstall` doesn't destroy your data):

- The PVC (`<release>-data`) holding your SQLite database.
- The application Secret (`<release>-app`) holding your `APP_SECRET_KEY`
  and `JWT_SECRET`.

To fully purge:

```bash
kubectl delete pvc -n foyre -l app.kubernetes.io/name=foyre
kubectl delete secret -n foyre -l app.kubernetes.io/name=foyre
kubectl delete namespace foyre
```

## Troubleshooting

**The seed Job fails on first install.**
Check `kubectl -n foyre logs job/<release>-seed-1`. The most common
cause is the seed admin password being too short or otherwise invalid;
the next is the `APP_SECRET_KEY` not being a valid Fernet key (it
should be 32 url-safe-base64 bytes — the chart generates this for you,
but if you provided your own, double-check).

**Pod stays in `Pending` with `unbound PVC`.**
Your cluster has no default StorageClass. Either install one (e.g.
[`local-path-provisioner`](https://github.com/rancher/local-path-provisioner))
and re-run the install, or set `persistence.enabled: false` and use
Postgres.

**Frontend loads but `/api/...` requests get 404 / HTML.**
This usually means the SPA fallback is catching API routes. Verify by
calling `kubectl exec` into the pod and `curl localhost:8000/api/auth/login`
— it should return JSON, not HTML. If it returns HTML, you may have
edited the route order in `app/main.py`; the `_spa_fallback` route
must be registered last.

**Validation env stays in `provisioning` forever.**
Check the backend logs. The most common causes:
- The host cluster has no StorageClass (vcluster needs persistent
  storage by default — install `local-path-provisioner` on the host).
- The host cluster's StorageClass uses `WaitForFirstConsumer` mode
  AND has no schedulable nodes that match the PVC's constraints.
- Network policy on the host cluster blocks Foyre from talking to it.
  Test the host kubeconfig from inside Foyre's pod with
  `kubectl exec deploy/foyre -- kubectl --kubeconfig=- ...`.

**Validation env is `ready` but the kubeconfig won't connect.**
The kubeconfig points at the host cluster's NodePort. The requester
needs to be able to reach `<external-node-host>:<nodePort>` from
their machine. Check that you set `external_node_host` in the host
cluster config to a hostname / IP that's reachable from where
requesters run `kubectl` — by default it falls back to the host's
InternalIP, which usually isn't externally reachable.

**Helm install reports `seed.admin.password must be set when seed.enabled is true`.**
The chart refuses to install with an empty seed password. Either:
- Pass `--set seed.admin.password=...` (or set it in your values), or
- Disable seeding with `--set seed.enabled=false` if you'll create the
  admin manually.

## Rotating the JWT secret

You can rotate `JWT_SECRET` at any time — existing sessions will
become invalid and users will need to sign in again, but no data is
lost. With the chart-managed Secret:

```bash
kubectl -n foyre delete secret <release>-app   # the chart will regenerate
helm upgrade foyre deploy/helm/foyre -n foyre --reuse-values --recreate-pods
```

With an `existingSecret`, edit the Secret in your secret-management
tool of choice and roll the pods.

## Rotating the Fernet APP_SECRET_KEY

This is **destructive** — you'll need to re-add any host kubeconfigs
configured in the UI after rotation, since they'll no longer decrypt.
Currently there is no in-app re-encryption flow. If you need to
rotate, the safest path is:

1. Note which host clusters are configured (write down their kubeconfigs).
2. Update the Secret with a new key.
3. Roll the pods.
4. Re-add each host cluster in **Administration → Validation environments**.

A future Foyre release may add a managed re-encryption flow.

## Security checklist

Before exposing Foyre to real users:

- [ ] `seed.admin.password` rotated to a strong value, then changed
      again at first login.
- [ ] `APP_SECRET_KEY` and `JWT_SECRET` set to long random values
      (the chart generates these for you on first install).
- [ ] TLS terminated at the Ingress with a real certificate.
- [ ] Network policy in place to limit who can reach the Service if
      you're on a shared cluster.
- [ ] Database backups configured (Postgres) or PVC snapshots scheduled
      (SQLite).
- [ ] `APP_SECRET_KEY` Secret backed up to your password manager /
      secrets store.
- [ ] If using `existingSecret` for the application secrets, restrict
      RBAC `get/list secrets` in the namespace.
