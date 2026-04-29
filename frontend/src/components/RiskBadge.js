import { jsx as _jsx } from "react/jsx-runtime";
const LABELS = {
    low: "Low",
    medium: "Medium",
    high: "High",
    unknown: "Unknown",
};
export function RiskBadge({ level }) {
    if (!level)
        return _jsx("span", { className: "muted", children: "\u2014" });
    return (_jsx("span", { className: "badge", "data-risk": level, children: LABELS[level] }));
}
