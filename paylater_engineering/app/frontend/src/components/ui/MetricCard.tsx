import type { ReactNode } from "react";

type MetricCardProps = { label: string; value: string; detail?: string; icon: ReactNode; tone?: "blue" | "green" | "amber" | "red" };

export function MetricCard({ label, value, detail, icon, tone = "blue" }: MetricCardProps) {
  return <article className="metric-card"><div className={`metric-icon metric-${tone}`}>{icon}</div><div><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong>{detail && <span className="metric-detail">{detail}</span>}</div></article>;
}
