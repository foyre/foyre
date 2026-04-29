# foyre-backend

The Foyre backend — a FastAPI service that serves the intake workflow,
validation-environment provisioning, authentication, and admin surfaces.

For a product overview and quick start, see the
[root README](../README.md).

## Stack

- Python 3.11+
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.x](https://www.sqlalchemy.org/) with SQLite (Postgres-ready)
- [Pydantic v2](https://docs.pydantic.dev/)
- [python-jose](https://python-jose.readthedocs.io/) for JWT
- [bcrypt](https://github.com/pyca/bcrypt) for password hashing
- [cryptography](https://cryptography.io/) for encrypting kubeconfigs
- [kubernetes](https://github.com/kubernetes-client/python) for host-cluster interactions
- [vcluster CLI](https://www.vcluster.com) — shelled out for cluster lifecycle

## Run locally

From the repo root, use `make install`, `make seed`, and `make run`. Or
manually:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then edit APP_SECRET_KEY etc.
python -m app.seed               # create DB + initial admin
uvicorn app.main:app --reload
```

API: <http://localhost:8000>. Interactive docs at `/docs`.

## Layout

```
app/
  main.py              FastAPI app factory and router wiring
  config.py            Settings loaded from env / .env
  db.py                SQLAlchemy engine, session, and Base
  deps.py              FastAPI dependencies (current user, role guards)

  domain/              Canonical enums and the intake-form schema
  models/              SQLAlchemy ORM models
  schemas/             Pydantic DTOs for request / response bodies
  repositories/        Thin DB access layer

  auth/                Authentication service, JWT tokens, pluggable
                       provider interface (local today; LDAP/AD/OIDC
                       land here later)
  services/            Business logic: request lifecycle, workflow,
                       risk classification, comments, history
  provisioning/        Validation environment orchestration, kube
                       client, encryption helpers, provider modules

  api/                 HTTP route modules
  seed.py              Bootstrap the database and initial admin user
```

## Environment variables

See [`.env.example`](./.env.example) for the full list. Required in any
real deployment:

| Variable         | Purpose                                                       |
|------------------|---------------------------------------------------------------|
| `APP_SECRET_KEY` | Fernet key for encrypting kubeconfigs at rest.                |
| `JWT_SECRET`     | Secret for signing JWT access tokens.                         |
| `DATABASE_URL`   | SQLAlchemy URL; SQLite for dev, Postgres recommended for prod.|
