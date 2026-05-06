#!/usr/bin/env bash
# Print the Kubernetes namespace used for Helm deploys from CI.
# Usage: k8s-deploy-namespace.sh <ref_name> <ref_type>
#   ref_name: github.ref_name (branch short name or tag without refs/*)
#   ref_type: github.ref_type — "branch" or "tag"
#
# Rules (must stay in sync with cleanup-feature-namespace workflow):
#   - tag push, or branch "main"  → foyre
#   - any other branch            → foyre-<slug> (RFC 1123-ish, max 63 chars)
set -euo pipefail

REF_NAME="${1:?ref name}"
REF_TYPE="${2:?ref type}"

if [ "$REF_TYPE" = "tag" ]; then
  echo foyre
  exit 0
fi
if [ "$REF_NAME" = "main" ]; then
  echo foyre
  exit 0
fi

safe=$(echo "$REF_NAME" | tr '[:upper:]' '[:lower:]' | sed 's|/|-|g' | tr -cd 'a-z0-9-' | sed 's/^-*//;s/-*$//' | tr -s '-')
if [ -z "$safe" ]; then
  safe=unknown
fi
ns="foyre-${safe}"
# Kubernetes namespace max length 63
echo "${ns}" | cut -c1-63
