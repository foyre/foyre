import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { HostClusterList } from "../../features/settings/HostClusterList";
export function AdminValidationEnvironmentsPage() {
    return (_jsxs("div", { children: [_jsx("p", { className: "muted", style: { marginTop: 0, marginBottom: 12 }, children: "Host Kubernetes cluster(s) that Foyre uses to create isolated validation environments (vclusters) for requesters to deploy into." }), _jsx(HostClusterList, {})] }));
}
