#!/usr/bin/env bash
# Foyre release automation.
#
# Cuts a clean release across:
#   1. Pre-flight checks (clean tree, on main, tests pass, helm lint passes).
#   2. Git tag (vX.Y.Z, signed if you have a key, force-replaces a stale tag).
#   3. CHANGELOG sanity check (warns if the new version isn't in the file).
#   4. Helm chart packaged and published to gh-pages branch (with merged index).
#   5. Pushes the tag (which triggers the GitHub Actions image build).
#
# The container image is published automatically by GitHub Actions when the
# tag is pushed (multi-arch, semver tags + sha-<short>).
#
# Usage:
#   bash scripts/release.sh                    # interactive (asks before each destructive step)
#   bash scripts/release.sh --dry-run          # print everything, change nothing
#   bash scripts/release.sh --yes              # answer yes to every prompt (use in scripts)
#   APP_VERSION=0.1.0 CHART_VERSION=0.2.0 bash scripts/release.sh --yes
#
# Defaults:
#   APP_VERSION    = appVersion in deploy/helm/foyre/Chart.yaml (current: 0.1.0)
#   CHART_VERSION  = version in    deploy/helm/foyre/Chart.yaml (current: 0.2.0)
#   GIT_TAG        = v$APP_VERSION
#   HELM_REPO_URL  = https://foyre.github.io/foyre/
#   GH_PAGES_BRANCH = gh-pages
#
# Required tools: git, helm 3.10+, awk, sed, curl. Optional: gh (for the
# GitHub Release step at the end).
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CHART_DIR="deploy/helm/foyre"
HELM_REPO_URL="${HELM_REPO_URL:-https://foyre.github.io/foyre/}"
GH_PAGES_BRANCH="${GH_PAGES_BRANCH:-gh-pages}"
DOCKER_IMAGE="${DOCKER_IMAGE:-zfeldstein/foyre}"
BITNAMI_REPO_URL="https://charts.bitnami.com/bitnami"

DRY_RUN=false
YES=false
SKIP_TESTS=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --yes|-y) YES=true ;;
    --skip-tests) SKIP_TESTS=true ;;
    --help|-h)
      sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown arg: $arg"; exit 2 ;;
  esac
done

APP_VERSION="${APP_VERSION:-$(awk '/^appVersion:/ {gsub(/"/,"",$2); print $2}' "$CHART_DIR/Chart.yaml")}"
CHART_VERSION="${CHART_VERSION:-$(awk '/^version:/ {print $2; exit}' "$CHART_DIR/Chart.yaml")}"
GIT_TAG="${GIT_TAG:-v${APP_VERSION}}"
RELEASE_DATE="$(date +%Y-%m-%d)"

# ---------------------------------------------------------------------------
# Pretty output
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
  BOLD=$'\033[1m';   DIM=$'\033[2m';  RESET=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; BOLD=""; DIM=""; RESET=""
fi

step()    { echo "${BOLD}${GREEN}==>${RESET} ${BOLD}$*${RESET}"; }
substep() { echo "  ${DIM}-${RESET} $*"; }
warn()    { echo "  ${YELLOW}WARN:${RESET} $*"; }
err()     { echo "${RED}ERROR:${RESET} $*" >&2; exit 1; }

run() {
  if [ "$DRY_RUN" = true ]; then
    echo "  ${DIM}[dry-run] $*${RESET}"
  else
    echo "  ${DIM}\$${RESET} $*"
    eval "$@"
  fi
}

confirm() {
  local prompt="$1"
  if [ "$YES" = true ] || [ "$DRY_RUN" = true ]; then
    echo "  ${DIM}[auto-yes] ${prompt}${RESET}"
    return 0
  fi
  read -rp "  ${YELLOW}? ${prompt} [y/N]: ${RESET}" ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

# ---------------------------------------------------------------------------
# 0. Banner
# ---------------------------------------------------------------------------
echo
echo "${BOLD}Foyre release${RESET}"
echo "  App version    ${BOLD}${APP_VERSION}${RESET}     (image tag: ${DOCKER_IMAGE}:${APP_VERSION})"
echo "  Chart version  ${BOLD}${CHART_VERSION}${RESET}     (foyre-${CHART_VERSION}.tgz)"
echo "  Git tag        ${BOLD}${GIT_TAG}${RESET}"
echo "  Helm repo      ${HELM_REPO_URL}"
echo "  Mode           $([ "$DRY_RUN" = true ] && echo dry-run || echo live)"
echo

if ! confirm "Proceed with these versions"; then
  err "aborted by user"
fi

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
step "1/6 Pre-flight checks"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$current_branch" != "main" ]; then
  warn "current branch is '$current_branch', not 'main'."
  if ! confirm "Continue anyway"; then err "release must come from main"; fi
fi

if [ -n "$(git status --porcelain)" ]; then
  git status --short
  if [ "$DRY_RUN" = true ]; then
    warn "working tree is dirty (allowed in --dry-run for previewing)"
  else
    err "working tree is dirty; commit or stash before releasing"
  fi
else
  substep "working tree clean"
fi

substep "fetching latest origin"
run "git fetch --quiet --tags origin"

upstream_sha="$(git rev-parse origin/main 2>/dev/null || echo "")"
local_sha="$(git rev-parse HEAD)"
if [ -n "$upstream_sha" ] && [ "$upstream_sha" != "$local_sha" ]; then
  warn "local main ($local_sha) differs from origin/main ($upstream_sha)."
  if ! confirm "Continue anyway"; then err "sync with origin/main first"; fi
fi

if [ "$SKIP_TESTS" = false ]; then
  if [ -d backend/.venv ]; then
    substep "running pytest"
    run "backend/.venv/bin/python -m pytest backend/tests/ -q --tb=short"
  else
    warn "backend/.venv not found; skipping pytest. Run 'make install && make test' first or pass --skip-tests."
    if ! confirm "Continue without running pytest"; then err "run tests first"; fi
  fi
fi

substep "helm dependency build (uses Chart.lock)"
run "helm repo add bitnami $BITNAMI_REPO_URL --force-update >/dev/null"
run "helm dependency build $CHART_DIR >/dev/null"

substep "helm lint"
# Chart rejects the placeholder password at render time; pass a throwaway
# so the lint exercises templating without flagging a fake security issue.
run "helm lint $CHART_DIR --set-string seed.admin.password='release-lint-check'"

# ---------------------------------------------------------------------------
# 2. CHANGELOG sanity
# ---------------------------------------------------------------------------
step "2/6 CHANGELOG sanity"

if grep -qE "^## \[${APP_VERSION}\]" CHANGELOG.md; then
  substep "found section [${APP_VERSION}] in CHANGELOG.md"
else
  warn "CHANGELOG.md has no [${APP_VERSION}] section."
  if ! confirm "Continue without a CHANGELOG entry for ${APP_VERSION}"; then
    err "add a [${APP_VERSION}] section to CHANGELOG.md and rerun"
  fi
fi

# ---------------------------------------------------------------------------
# 3. Git tag
# ---------------------------------------------------------------------------
step "3/6 Create tag ${GIT_TAG}"

# Detect signing capability.
if git config --get user.signingkey >/dev/null 2>&1; then
  TAG_FLAG="-s"
  substep "tags will be GPG-signed (-s)"
else
  TAG_FLAG="-a"
  substep "no signing key configured; using annotated tag (-a)"
fi

# If the tag already exists locally, we'll force-replace it after confirm.
if git rev-parse "$GIT_TAG" >/dev/null 2>&1; then
  warn "local tag ${GIT_TAG} already exists at $(git rev-parse "$GIT_TAG"^{} 2>/dev/null | cut -c1-7)"
  if confirm "Force-replace ${GIT_TAG} with current HEAD ($(git rev-parse --short HEAD))"; then
    run "git tag -d $GIT_TAG"
  else
    err "tag exists; aborting"
  fi
fi

run "git tag $TAG_FLAG $GIT_TAG -m '${GIT_TAG} — Foyre ${APP_VERSION}'"
substep "created tag ${GIT_TAG}"

# ---------------------------------------------------------------------------
# 4. Package the Helm chart
# ---------------------------------------------------------------------------
step "4/6 Package Helm chart ${CHART_VERSION}"

DIST_DIR=".helm-dist"
run "rm -rf $DIST_DIR && mkdir -p $DIST_DIR"
run "helm package $CHART_DIR --destination $DIST_DIR"

PKG="${DIST_DIR}/foyre-${CHART_VERSION}.tgz"
if [ "$DRY_RUN" = false ] && [ ! -f "$PKG" ]; then
  err "expected $PKG was not produced"
fi
substep "produced $PKG"

# Pull the existing index (if any) and merge.
substep "merging index from $HELM_REPO_URL"
if [ "$DRY_RUN" = false ]; then
  if curl -fsSL "${HELM_REPO_URL}index.yaml" -o "$DIST_DIR/index-prior.yaml" 2>/dev/null; then
    helm repo index "$DIST_DIR" --url "$HELM_REPO_URL" --merge "$DIST_DIR/index-prior.yaml"
  else
    warn "no existing index at ${HELM_REPO_URL}index.yaml; creating fresh index"
    helm repo index "$DIST_DIR" --url "$HELM_REPO_URL"
  fi
else
  echo "  ${DIM}[dry-run] curl + helm repo index --merge${RESET}"
fi

# ---------------------------------------------------------------------------
# 5. Publish to gh-pages
# ---------------------------------------------------------------------------
step "5/6 Publish chart to ${GH_PAGES_BRANCH}"

WT="$(mktemp -d -t foyre-gh-pages.XXXXXX)"
cleanup_wt() {
  if [ -d "$WT/.git" ] || [ -f "$WT/.git" ]; then
    git worktree remove --force "$WT" >/dev/null 2>&1 || true
  fi
  rm -rf "$WT" 2>/dev/null || true
}
trap cleanup_wt EXIT

if git rev-parse "origin/$GH_PAGES_BRANCH" >/dev/null 2>&1; then
  substep "fetching $GH_PAGES_BRANCH from origin"
  run "git worktree add $WT origin/$GH_PAGES_BRANCH"
else
  warn "origin/$GH_PAGES_BRANCH does not exist yet; will create an orphan branch"
  run "git worktree add --detach $WT HEAD"
  run "git -C $WT switch --orphan $GH_PAGES_BRANCH"
  # Clear the orphan working tree of any tracked files.
  run "git -C $WT rm -rf . >/dev/null 2>&1 || true"
fi

substep "copying packaged chart and merged index"
run "cp -f $DIST_DIR/foyre-${CHART_VERSION}.tgz $WT/"
run "cp -f $DIST_DIR/index.yaml $WT/"
run "git -C $WT add foyre-${CHART_VERSION}.tgz index.yaml"

if [ "$DRY_RUN" = false ] && git -C "$WT" diff --staged --quiet; then
  warn "no chart changes staged on $GH_PAGES_BRANCH; chart ${CHART_VERSION} is already published or identical"
else
  run "git -C $WT commit -s -m 'Publish Helm chart ${CHART_VERSION}'"
fi

# ---------------------------------------------------------------------------
# 6. Push everything
# ---------------------------------------------------------------------------
step "6/6 Push tag and ${GH_PAGES_BRANCH}"

if confirm "Push tag ${GIT_TAG} to origin (force, since stale tag will be replaced)"; then
  run "git push --force origin $GIT_TAG"
  substep "pushed ${GIT_TAG} — GitHub Actions will build & push image ${DOCKER_IMAGE}:${APP_VERSION}"
else
  warn "tag NOT pushed; you can push later with:"
  echo "    git push --force origin $GIT_TAG"
fi

if confirm "Push ${GH_PAGES_BRANCH} to origin"; then
  run "git -C $WT push origin $GH_PAGES_BRANCH"
  substep "pushed Helm chart ${CHART_VERSION} to ${HELM_REPO_URL}"
else
  warn "${GH_PAGES_BRANCH} NOT pushed; you can push later with:"
  echo "    git -C $WT push origin $GH_PAGES_BRANCH"
  echo "  ${DIM}(worktree path: $WT — keep it until you push, or repackage from scratch)${RESET}"
  trap - EXIT
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
step "Done"

cat <<EOF

  Image    docker pull ${DOCKER_IMAGE}:${APP_VERSION}
           (built by GitHub Actions when the tag landed; check the
            "Container image" workflow on the ${GIT_TAG} ref)

  Chart    helm repo add foyre ${HELM_REPO_URL}
           helm repo update
           helm install foyre foyre/foyre --version ${CHART_VERSION} \\
             --namespace foyre --create-namespace \\
             --set seed.admin.password='change-me'

  GitHub   Draft a release in the UI, or:
           gh release create ${GIT_TAG} --title 'Foyre ${APP_VERSION}' \\
             --notes-file <(awk '/^## \\[${APP_VERSION}\\]/{flag=1;print;next} /^## \\[/{flag=0} flag' CHANGELOG.md)

EOF
