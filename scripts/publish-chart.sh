#!/usr/bin/env bash
# Publish the current Foyre Helm chart to the GitHub Pages Helm repo.
#
# Does ONLY chart publishing — no git tags, no image. Idempotent: rerun safely.
#
# Reads deploy/helm/foyre/Chart.yaml to find the chart version, packages it,
# merges with the current published index.yaml, and pushes to gh-pages.
#
# Usage:
#   bash scripts/publish-chart.sh                # interactive
#   bash scripts/publish-chart.sh --yes          # no prompts
#   bash scripts/publish-chart.sh --dry-run      # change nothing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CHART_DIR="deploy/helm/foyre"
HELM_REPO_URL="${HELM_REPO_URL:-https://foyre.github.io/foyre/}"
GH_PAGES_BRANCH="${GH_PAGES_BRANCH:-gh-pages}"
BITNAMI_REPO_URL="https://charts.bitnami.com/bitnami"

DRY_RUN=false
YES=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --yes|-y)  YES=true ;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown arg: $arg"; exit 2 ;;
  esac
done

CHART_VERSION="${CHART_VERSION:-$(awk '/^version:/ {print $2; exit}' "$CHART_DIR/Chart.yaml")}"
PKG_NAME="foyre-${CHART_VERSION}.tgz"

if [ -t 1 ]; then
  G=$'\033[32m'; Y=$'\033[33m'; D=$'\033[2m'; B=$'\033[1m'; R=$'\033[0m'
else G=""; Y=""; D=""; B=""; R=""; fi

step()    { echo "${B}${G}==>${R} ${B}$*${R}"; }
substep() { echo "  ${D}-${R} $*"; }
warn()    { echo "  ${Y}WARN:${R} $*"; }
err()     { echo "ERROR: $*" >&2; exit 1; }

run() {
  if [ "$DRY_RUN" = true ]; then
    echo "  ${D}[dry-run] $*${R}"
  else
    echo "  ${D}\$${R} $*"
    eval "$@"
  fi
}

confirm() {
  if [ "$YES" = true ] || [ "$DRY_RUN" = true ]; then
    echo "  ${D}[auto-yes] $*${R}"
    return 0
  fi
  read -rp "  ${Y}? $* [y/N]: ${R}" ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

# ---------------------------------------------------------------------------
echo
echo "${B}Foyre chart publish${R}"
echo "  Chart version    ${B}${CHART_VERSION}${R}    (${PKG_NAME})"
echo "  Helm repo URL    ${HELM_REPO_URL}"
echo "  gh-pages branch  ${GH_PAGES_BRANCH}"
echo "  Mode             $([ "$DRY_RUN" = true ] && echo dry-run || echo live)"
echo

confirm "Proceed" || err "aborted"

# 1. Fetch chart dependencies (Bitnami Postgres subchart, pinned by Chart.lock).
step "1/4 Fetch chart dependencies"
run "helm repo add bitnami $BITNAMI_REPO_URL --force-update >/dev/null"
run "helm dependency build $CHART_DIR >/dev/null"
substep "subchart fetched into $CHART_DIR/charts/"

# 2. Package the chart.
step "2/4 Package chart"
DIST=".helm-dist"
run "rm -rf $DIST && mkdir -p $DIST"
run "helm package $CHART_DIR --destination $DIST"
[ "$DRY_RUN" = false ] && [ ! -f "$DIST/$PKG_NAME" ] && err "expected $DIST/$PKG_NAME was not produced"
substep "produced $DIST/$PKG_NAME"

# 3. Merge with the currently-published index.
step "3/4 Build merged index"
if [ "$DRY_RUN" = false ]; then
  if curl -fsSL "${HELM_REPO_URL}index.yaml" -o "$DIST/index-prior.yaml" 2>/dev/null; then
    substep "merging with $HELM_REPO_URL"
    helm repo index "$DIST" --url "$HELM_REPO_URL" --merge "$DIST/index-prior.yaml"
  else
    warn "no existing index at ${HELM_REPO_URL}; creating fresh"
    helm repo index "$DIST" --url "$HELM_REPO_URL"
  fi
  echo "  Versions in new index:"
  awk '/^[[:space:]]+- /{ next } /^[[:space:]]+name: foyre$/{ getline v; sub(/.*version: /, "", v); print "    foyre/" v }' "$DIST/index.yaml" || true
else
  echo "  ${D}[dry-run] curl + helm repo index --merge${R}"
fi

# 4. Commit to gh-pages worktree and push.
step "4/4 Commit & push to ${GH_PAGES_BRANCH}"

WT="$(mktemp -d -t foyre-gh-pages.XXXXXX)"
cleanup_wt() {
  if [ -d "$WT" ]; then
    git worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"
  fi
}
trap cleanup_wt EXIT

run "git fetch --quiet origin $GH_PAGES_BRANCH"

if git rev-parse "origin/$GH_PAGES_BRANCH" >/dev/null 2>&1; then
  run "git worktree add $WT origin/$GH_PAGES_BRANCH"
else
  warn "origin/$GH_PAGES_BRANCH does not exist yet; creating orphan"
  run "git worktree add --detach $WT HEAD"
  run "git -C $WT switch --orphan $GH_PAGES_BRANCH"
  run "git -C $WT rm -rf . >/dev/null 2>&1 || true"
fi

run "cp -f $DIST/$PKG_NAME $WT/"
run "cp -f $DIST/index.yaml $WT/"
run "git -C $WT add $PKG_NAME index.yaml"

if [ "$DRY_RUN" = false ]; then
  if git -C "$WT" diff --staged --quiet; then
    warn "no changes — gh-pages is already up to date for chart ${CHART_VERSION}"
    trap - EXIT
    cleanup_wt
    exit 0
  fi
fi

run "git -C $WT commit -s -m 'Publish Helm chart ${CHART_VERSION}'"

if confirm "Push to origin/${GH_PAGES_BRANCH}"; then
  run "git -C $WT push origin HEAD:refs/heads/$GH_PAGES_BRANCH"
  substep "pushed; ${HELM_REPO_URL} will serve $PKG_NAME in a minute or two"
else
  warn "not pushed; run this when ready:"
  echo "    git -C $WT push origin HEAD:refs/heads/$GH_PAGES_BRANCH"
  trap - EXIT
fi

echo
echo "${B}Verify:${R}"
echo "  helm repo update foyre"
echo "  helm search repo foyre/foyre --versions"
