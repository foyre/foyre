import { HostClusterList } from "../../features/settings/HostClusterList";

export function AdminValidationEnvironmentsPage() {
  return (
    <div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
        Host Kubernetes cluster(s) that Foyre uses to create isolated
        validation environments (vclusters) for requesters to deploy into.
      </p>
      <HostClusterList />
    </div>
  );
}
