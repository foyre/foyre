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
  - apiGroups: [""]
    resources: [namespaces, pods, services, configmaps, secrets,
                serviceaccounts, persistentvolumeclaims]
    verbs: ["*"]
  - apiGroups: [apps]
    resources: [statefulsets, deployments, replicasets]
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

          <h5 style={{ marginBottom: 4 }}>3. Mint a kubeconfig for that service account</h5>
          <pre
            style={{
              background: "var(--bg-soft)",
              padding: 8,
              borderRadius: "var(--radius)",
              overflow: "auto",
              fontSize: 12,
            }}
          >
{`kubectl -n foyre-system create token foyre-provisioner --duration=8760h`}
          </pre>
          <p className="muted">
            Take the token above and compose a kubeconfig YAML with your
            cluster's API URL + CA certificate. Paste the resulting kubeconfig
            into the form below, then click <strong>Test connection</strong>{" "}
            before saving.
          </p>

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
