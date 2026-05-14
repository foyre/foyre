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
  - apiGroups: [rbac.authorization.k8s.io]
    resources: [roles, rolebindings, clusterroles, clusterrolebindings]
    verbs: [get, list, create, delete, patch]
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
  return (
    <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          color: "var(--accent)",
          fontWeight: 500,
        }}
      >
        {open ? "\u25BE" : "\u25B8"} Setup guide: preparing a host cluster
      </button>

      {open && (
        <div style={{ marginTop: 12, lineHeight: 1.6 }}>
          <p>
            Foyre needs a Kubernetes cluster it can create virtual clusters
            inside. Any k8s cluster works — RKE2, k3s, EKS, GKE, AKS. The steps
            below configure a service account with just enough permissions to
            provision and tear down validation environments.
          </p>

          <h5 style={{ marginBottom: 4 }}>1. Install a StorageClass (if missing)</h5>
          <p className="muted" style={{ marginTop: 0 }}>
            vcluster needs persistent storage. If <code>kubectl get sc</code>{" "}
            shows no default, install Rancher's local-path-provisioner:
          </p>
          <pre
            style={{
              background: "var(--bg-soft)",
              padding: 8,
              borderRadius: "var(--radius)",
              overflow: "auto",
              fontSize: 12,
            }}
          >
{`kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'`}
          </pre>

          <h5 style={{ marginBottom: 4 }}>2. Create the Foyre namespace + RBAC</h5>
          <p className="muted" style={{ marginTop: 0 }}>
            This creates a service account with the permissions Foyre needs.
          </p>
          <pre
            style={{
              background: "var(--bg-soft)",
              padding: 8,
              borderRadius: "var(--radius)",
              overflow: "auto",
              fontSize: 12,
            }}
          >
{`kubectl create namespace foyre-system
kubectl apply -f - <<'EOF'
${RBAC_YAML}EOF`}
          </pre>

          <h5 style={{ marginBottom: 4 }}>3. Generate a kubeconfig for that service account</h5>
          <p className="muted" style={{ marginTop: 0 }}>
            This one-liner reads the API server URL and CA cert from your
            current kubectl context, mints a 1-year token for the service
            account, and prints a complete kubeconfig YAML — no hand-editing.
          </p>
          <pre
            style={{
              background: "var(--bg-soft)",
              padding: 8,
              borderRadius: "var(--radius)",
              overflow: "auto",
              fontSize: 12,
            }}
          >
{`SA_NS=foyre-system
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
EOF`}
          </pre>
          <p className="muted">
            Paste the YAML it prints into the form below, then click{" "}
            <strong>Test connection</strong> before saving.
          </p>
          <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Sanity check the service account first — these should all print
            <code> yes</code>. Any <code>no</code> means the ClusterRole in
            step 2 didn't apply cleanly; re-run step 2.
          </p>
          <pre
            style={{
              background: "var(--bg-soft)",
              padding: 8,
              borderRadius: "var(--radius)",
              overflow: "auto",
              fontSize: 12,
            }}
          >
{`SA=system:serviceaccount:foyre-system:foyre-provisioner
kubectl auth can-i list nodes                     --as=$SA
kubectl auth can-i list storageclasses            --as=$SA
kubectl auth can-i create namespaces              --as=$SA
kubectl auth can-i create clusterrolebindings     --as=$SA
kubectl auth can-i create selfsubjectaccessreviews --as=$SA`}
          </pre>

          <h5 style={{ marginBottom: 4 }}>4. External access (for requesters' kubectl)</h5>
          <p className="muted" style={{ marginTop: 0 }}>
            Foyre exposes each validation cluster via a NodePort service. Set{" "}
            <strong>External node host</strong> to the hostname or IP at which
            your cluster's worker nodes are reachable from the requester's
            machine (e.g. <code>k8s.internal.example.com</code> or a node IP).
            If left blank, Foyre will use the node's InternalIP, which may
            not be reachable from outside.
          </p>

          <h5 style={{ marginBottom: 4, color: "var(--danger)" }}>
            Security note
          </h5>
          <p className="muted" style={{ marginTop: 0 }}>
            The kubeconfig you paste here has broad permissions on your host
            cluster. Foyre encrypts it at rest using{" "}
            <code>APP_SECRET_KEY</code> but never returns it via the API. Rotate
            the service-account token periodically per your org's policy.
          </p>
        </div>
      )}
    </div>
  );
}
