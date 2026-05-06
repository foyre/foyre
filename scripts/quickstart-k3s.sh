#!/usr/bin/env bash
# Bootstrap a single-node k3s lab and install Foyre with Helm.
#
# Intended for a fresh Ubuntu VM where you want the quickest possible demo.
# It installs k3s using the official installer, installs Helm if missing, then
# installs/updates Foyre from the published Helm repo.
set -euo pipefail

RELEASE="${RELEASE:-foyre}"
NAMESPACE="${NAMESPACE:-foyre}"
HELM_REPO_NAME="${HELM_REPO_NAME:-foyre}"
HELM_REPO_URL="${HELM_REPO_URL:-https://foyre.github.io/foyre/}"
CHART="${CHART:-foyre/foyre}"
SEED_ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-}"

if [ -z "$SEED_ADMIN_PASSWORD" ]; then
  if command -v openssl >/dev/null 2>&1; then
    SEED_ADMIN_PASSWORD="Foyre-$(openssl rand -hex 8)"
  else
    SEED_ADMIN_PASSWORD="Foyre-change-me-$(date +%s)"
  fi
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required for this quickstart." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "Installing k3s..."
  curl -sfL https://get.k3s.io | sh -
  mkdir -p "$HOME/.kube"
  sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
  sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
  export KUBECONFIG="$HOME/.kube/config"
else
  export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "Installing Helm..."
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

echo "Waiting for Kubernetes node readiness..."
kubectl wait --for=condition=Ready node --all --timeout=180s

echo "Installing Foyre..."
helm repo add "$HELM_REPO_NAME" "$HELM_REPO_URL" >/dev/null 2>&1 || true
helm repo update "$HELM_REPO_NAME"

helm upgrade --install "$RELEASE" "$CHART" \
  --namespace "$NAMESPACE" --create-namespace \
  --set service.type=NodePort \
  --set-string "seed.admin.password=${SEED_ADMIN_PASSWORD}" \
  --wait --timeout 15m

NODE_IP="$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')"
NODE_PORT="$(kubectl -n "$NAMESPACE" get svc "$RELEASE" -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')"

cat <<EOF

Foyre is installed.

Web UI:
  http://${NODE_IP}:${NODE_PORT}/

Login:
  username: admin
  password: ${SEED_ADMIN_PASSWORD}

Change this password after first login.

EOF
