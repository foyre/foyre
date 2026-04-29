import type { RiskLevel } from "../types/domain";

const LABELS: Record<RiskLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  unknown: "Unknown",
};

export function RiskBadge({ level }: { level: RiskLevel | null }) {
  if (!level) return <span className="muted">—</span>;
  return (
    <span className="badge" data-risk={level}>
      {LABELS[level]}
    </span>
  );
}
