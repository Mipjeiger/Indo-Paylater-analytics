import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CircleDollarSign, Percent, Users, WalletCards } from "lucide-react";
import { getDashboardKpis } from "../services/dashboard-service";
import { QueryState } from "../components/feedback/QueryState";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader } from "../components/ui/PageHeader";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export function OverviewPage() {
  const query = useQuery({ queryKey: ["dashboard-kpis"], queryFn: ({ signal }) => getDashboardKpis(signal), retry: false });
  return <><PageHeader eyebrow="Executive overview" title="Portfolio at a glance" description="A verified view of portfolio performance, exposure, and risk concentration." /><QueryState isLoading={query.isLoading} error={query.error} empty={!query.data}><div className="metric-grid">
    <MetricCard label="Total borrowers" value={query.data ? query.data.total_borrowers.toLocaleString() : "—"} icon={<Users size={19} />} />
    <MetricCard label="Active borrowers" value={query.data ? query.data.active_borrowers.toLocaleString() : "—"} icon={<WalletCards size={19} />} tone="green" />
    <MetricCard label="Outstanding exposure" value={query.data ? money.format(query.data.outstanding_exposure) : "—"} icon={<CircleDollarSign size={19} />} tone="amber" />
    <MetricCard label="Repayment rate" value={query.data ? `${(query.data.repayment_rate * 100).toFixed(1)}%` : "—"} icon={<Percent size={19} />} tone="blue" />
    <MetricCard label="TWP90 rate" value={query.data ? `${(query.data.twp90_rate * 100).toFixed(1)}%` : "—"} icon={<AlertCircle size={19} />} tone="red" />
  </div></QueryState><div className="panel-grid"><section className="panel panel-large"><div className="panel-heading"><div><span className="eyebrow">Portfolio performance</span><h3>Trend data is supplied by the backend</h3></div></div><div className="empty-chart"><BarPlaceholder /></div></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">Operational status</span><h3>Business data boundary</h3></div></div><p className="panel-copy">Charts and alerts remain unavailable until the corresponding aggregation endpoints are implemented. No sample values are shown.</p></section></div></>;
}

function BarPlaceholder() { return <div className="bar-placeholder"><span /><span /><span /><span /><span /><span /></div>; }
