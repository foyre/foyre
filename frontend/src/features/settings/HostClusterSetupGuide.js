import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from "react";
const RBAC_YAML = `apiVersion: v1
kind: ServiceAccount
metadata:
  name: foyre-provisioner
  namespace: foyre-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: foyre-provisioner
rules:
  # Read-only at the cluster level — needed for test-connection (list nodes)
  # and to pick a node IP for the per-request NodePort service.
  - apiGroups: [""]
    resources: [nodes]
    verbs: [get, list]
  # Self-permission checks used by test-connection.
  - apiGroups: [authorization.k8s.io]
    resources: [selfsubjectaccessreviews]
    verbs: [create]
  # Workload resources Foyre manages for each validation environment.
  - apiGroups: [""]
    resources: [namespaces, pods, services, configmaps, secrets,
                serviceaccounts, persistentvolumeclaims, events]
    verbs: ["*"]
  - apiGroups: [apps]
    resources: [statefulsets, deployments, replicasets]
    verbs: ["*"]
  - apiGroups: [batch]
    resources: [jobs]
    verbs: ["*"]
  # RBAC management. \`escalate\` + \`bind\` are required because vcluster
  # creates ClusterRoles with broad permissions and ClusterRoleBindings that
  # reference them; Kubernetes requires those verbs to delegate RBAC.
  - apiGroups: [rbac.authorization.k8s.io]
    resources: [roles, clusterroles]
    verbs: [get, list, watch, create, update, patch, delete, escalate, bind]
  - apiGroups: [rbac.authorization.k8s.io]
    resources: [rolebindings, clusterrolebindings]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [networkpolicies, ingresses]
    verbs: ["*"]
  - apiGroups: [storage.k8s.io]
    resources: [storageclasses]
    verbs: [get, list]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: foyre-provisioner
subjects:
  - { kind: ServiceAccount, name: foyre-provisioner, namespace: foyre-system }
roleRef:
  { kind: ClusterRole, name: foyre-provisioner, apiGroup: rbac.authorization.k8s.io }
`;
export function HostClusterSetupGuide() {
    const [open, setOpen] = useState(false);
    return (_jsxs("div", { className: "card", style: { marginBottom: 16, padding: "12px 16px" }, children: [_jsxs("button", { type: "button", onClick: () => setOpen((v) => !v), "aria-expanded": open, style: {
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    color: "var(--accent)",
                    fontWeight: 500,
                }, children: [open ? "\u25BE" : "\u25B8", " Setup guide: preparing a host cluster"] }), open && (_jsxs("div", { style: { marginTop: 12, lineHeight: 1.6 }, children: [_jsx("p", { children: "Foyre needs a Kubernetes cluster it can create virtual clusters inside. Any k8s cluster works \u2014 RKE2, k3s, EKS, GKE, AKS. The steps below configure a service account with just enough permissions to provision and tear down validation environments." }), _jsx("h5", { style: { marginBottom: 4 }, children: "1. Install a StorageClass (if missing)" }), _jsxs("p", { className: "muted", style: { marginTop: 0 }, children: ["vcluster needs persistent storage. If ", _jsx("code", { children: "kubectl get sc" }), " ", "shows no default, install Rancher's local-path-provisioner:"] }), _jsx("pre", { style: {
                            background: "var(--bg-soft)",
                            padding: 8,
                            borderRadius: "var(--radius)",
                            overflow: "auto",
                            fontSize: 12,
                        }, children: `kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'` }), _jsx("h5", { style: { marginBottom: 4 }, children: "2. Create the Foyre namespace + RBAC" }), _jsx("p", { className: "muted", style: { marginTop: 0 }, children: "This creates a service account with the permissions Foyre needs." }), _jsx("pre", { style: {
                            background: "var(--bg-soft)",
                            padding: 8,
                            borderRadius: "var(--radius)",
                            overflow: "auto",
                            fontSize: 12,
                        }, children: `kubectl create namespace foyre-system
kubectl apply -f - <<'EOF'
${RBAC_YAML}EOF` }), _jsx("h5", { style: { marginBottom: 4 }, children: "3. Generate a kubeconfig for that service account" }), _jsx("p", { className: "muted", style: { marginTop: 0 }, children: "This one-liner reads the API server URL and CA cert from your current kubectl context, mints a 1-year token for the service account, and prints a complete kubeconfig YAML \u2014 no hand-editing." }), _jsx("pre", { style: {
                            background: "var(--bg-soft)",
                            padding: 8,
                            borderRadius: "var(--radius)",
                            overflow: "auto",
                            fontSize: 12,
                        }, children: `SA_NS=foyre-system
SA_NAME=foyre-provisioner

# Read API server URL + CA from the *current* kubectl context.
SERVER=$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.server}')
CA=$(kubectl config view --raw --flatten --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
TOKEN=$(kubectl -n $SA_NS create token $SA_NAME --duration=8760h)

cat <<EOF
apiVersion: v1
kind: Config
clusters:
- name: foyre-host
  cluster:
    server: $SERVER
    certificate-authority-data: $CA
users:
- name: foyre-provisioner
  user:
    token: $TOKEN
contexts:
- name: foyre-host
  context:
    cluster: foyre-host
    user: foyre-provisioner
current-context: foyre-host
EOF` }), _jsxs("p", { className: "muted", children: ["Paste the YAML it prints into the form below, then click", " ", _jsx("strong", { children: "Test connection" }), " before saving."] }), _jsxs("p", { className: "muted", style: { fontSize: 12, marginTop: 4 }, children: ["Sanity check the service account first \u2014 these should all print", _jsx("code", { children: " yes" }), ". Any ", _jsx("code", { children: "no" }), " means the ClusterRole in step 2 didn't apply cleanly; re-run step 2."] }), _jsx("pre", { style: {
                            background: "var(--bg-soft)",
                            padding: 8,
                            borderRadius: "var(--radius)",
                            overflow: "auto",
                            fontSize: 12,
                        }, children: `SA=system:serviceaccount:foyre-system:foyre-provisioner
kubectl auth can-i list nodes                     --as=$SA
kubectl auth can-i list storageclasses            --as=$SA
kubectl auth can-i create namespaces              --as=$SA
kubectl auth can-i create clusterrolebindings     --as=$SA
kubectl auth can-i create selfsubjectaccessreviews --as=$SA` }), _jsx("h5", { style: { marginBottom: 4 }, children: "4. External access (for requesters' kubectl)" }), _jsxs("p", { className: "muted", style: { marginTop: 0 }, children: ["Foyre exposes each validation cluster via a NodePort service. Set", " ", _jsx("strong", { children: "External node host" }), " to the hostname or IP at which your cluster's worker nodes are reachable from the requester's machine (e.g. ", _jsx("code", { children: "k8s.internal.example.com" }), " or a node IP). If left blank, Foyre will use the node's InternalIP, which may not be reachable from outside."] }), _jsx("h5", { style: { marginBottom: 4, color: "var(--danger)" }, children: "Security note" }), _jsxs("p", { className: "muted", style: { marginTop: 0 }, children: ["The kubeconfig you paste here has broad permissions on your host cluster. Foyre encrypts it at rest using", " ", _jsx("code", { children: "APP_SECRET_KEY" }), " but never returns it via the API. Rotate the service-account token periodically per your org's policy."] })] }))] }));
}
