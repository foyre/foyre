# Contributing to Foyre

Thanks for your interest. Foyre is a young project and the easiest way to
help is to file clear issues, propose small focused pull requests, and ask
questions when the docs aren't clear.

By participating you agree to our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Reporting bugs and requesting features

- Search [existing issues](https://github.com/zfeldstein/foyre/issues)
  before opening a new one.
- **Bugs**: include what you ran, what you expected, and what happened.
  Versions help (Python, Node, OS, k8s distribution).
- **Features**: explain the problem you're trying to solve before
  proposing a specific solution. Concrete use cases beat abstractions.
- **Security issues must NOT be filed as public issues.** See
  [SECURITY.md](./SECURITY.md) for the private reporting process.

## Development setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- GNU Make
- (Optional) a Kubernetes cluster reachable from your dev machine for
  testing validation-environment features — `kind` or `k3d` work well
  locally.

### First-time setup

```bash
git clone https://github.com/zfeldstein/foyre.git
cd foyre
make install           # creates backend/.venv and installs deps
make front-install     # installs frontend deps
make env               # copies backend/.env.example -> backend/.env
```

Generate and set `APP_SECRET_KEY` in `backend/.env`:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then:

```bash
make seed              # create DB and initial admin user
make run               # backend on :8000
# in another terminal
make front             # frontend on :5173
```

### Resetting the database

```bash
make reset             # drops the local SQLite database
make seed              # re-seeds the admin user
```

Useful when you've changed model code — Foyre uses `Base.metadata.create_all`
for dev, so schema changes mean resetting the local database.

## Project layout

```
backend/app/           FastAPI application
frontend/src/          React + TypeScript UI
```

See [backend/README.md](./backend/README.md) and
[frontend/README.md](./frontend/README.md) for per-app details.

## Making changes

### Branch and commit

- Branch from `main`.
- Keep changes focused — one concern per PR. A small, obvious PR is
  easier to review and merge than a large one with "while I was here"
  edits.
- Write commit messages that explain *why*, not just *what*.

### Sign your commits (DCO)

Foyre requires all commits to be signed off under the
[Developer Certificate of Origin 1.1](https://developercertificate.org/).
This is a lightweight way for contributors to assert they have the right
to submit their changes. It does **not** assign copyright — you retain
yours.

To sign off a commit, append `-s` to `git commit`:

```bash
git commit -s -m "fix: handle empty payload in risk service"
```

This adds a `Signed-off-by: Your Name <your@email>` trailer to the
message. By signing off, you are agreeing to the DCO text in full.

If you forget, amend your last commit: `git commit --amend -s --no-edit`.
For multiple commits, rebase with `--signoff`.

### Coding standards

**Backend (Python)**

- Type-annotate public functions and Pydantic models.
- Raise `HTTPException` at the API layer; raise domain exceptions in
  services and translate them at the route boundary.
- All DB access goes through `repositories/` — services never touch
  sessions directly for CRUD.
- Status transitions MUST go through `services/workflow_service.py`. Do
  not mutate request status anywhere else.
- History MUST be written through `services/history_service.py`. Do not
  create `RequestHistoryEvent` rows directly.

**Frontend (TypeScript)**

- Prefer small, focused components.
- `api/` modules wrap HTTP calls; components don't import `fetch`.
- Use the existing design system (`styles.css`) before adding custom CSS.
- Keep types in `types/domain.ts` aligned with backend schemas. When
  backend DTOs change, update TS types in the same PR.

### Tests

The project is still building out a formal test suite. Contributions that
add pytest / Playwright coverage to existing features are welcome. For
changes that affect workflow, risk rules, or auth, include a test case
that demonstrates the new behavior even if the rest of that module isn't
covered yet.

### Typecheck and lint before opening a PR

```bash
# Backend
cd backend && source .venv/bin/activate && python -m compileall app

# Frontend
cd frontend && npx tsc -b --noEmit
```

### Continuous integration

GitHub Actions runs on every pull request and on pushes to `main`:

- **CI** (`.github/workflows/ci.yml`) — frontend production build, Python
  byte-compile of `backend/app`, and `helm lint` / `helm template` for the
  chart.
- **Container image** (`.github/workflows/container.yml`) — on pull
  requests, builds the multi-arch Docker image **without** pushing (safe for
  forks). On pushes to any branch and on `workflow_dispatch`, logs into
  Docker Hub and pushes `zfeldstein/foyre` with tags derived from the
  branch name, short SHA, and (for `v*` git tags) semver labels.

Repository maintainers must configure **Actions secrets**
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` for publishes to succeed. Use a
Docker Hub access token, not your account password.

## Pull requests

- Reference the issue your PR addresses (`Fixes #123`).
- Describe the user-visible behavior change, not just the
  implementation.
- Keep unrelated refactors separate — a one-concern PR is much more
  likely to merge quickly.
- Screenshots / terminal output help for UI and flow changes.

## Reviewers' commitments

PR authors should expect:

- A first response within a few business days.
- Specific, actionable review feedback rather than vague critique.
- An honest "no" when a change is out of scope, with a clear reason.

## Licensing of contributions

Foyre is licensed under the
[Apache License, Version 2.0](./LICENSE). By contributing a pull request,
you agree that your contribution is licensed to the project and to users
of the project under the same license, and that you have the right to
make that grant (the DCO sign-off confirms this).

If you want to discuss an approach before writing code — especially for
something non-trivial — open an issue first. Small aligned efforts ship
much faster than large surprises.
