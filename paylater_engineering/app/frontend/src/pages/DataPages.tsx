import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/PageHeader";
import { QueryState } from "../components/feedback/QueryState";
import {
  getAuditEvents,
  getBorrowers,
  getDecisions,
  getModels,
  getPortfolioSummary,
} from "../services/aggregate-service";

function formatMoney(value: number | null | undefined) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value ?? 0);
}

export function BorrowersPage() {
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["borrowers", search],
    queryFn: ({ signal }) => getBorrowers(50, 0, search || undefined, signal),
    retry: false,
  });

  return (
    <>
      <PageHeader eyebrow="Borrower intelligence" title="Borrowers" description="Verified borrower records from the FastAPI/PostgreSQL boundary." />
      <section className="panel">
        <div className="panel-heading"><div><span className="eyebrow">Search</span><h3>Borrower directory</h3></div></div>
        <label>Borrower ID
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ID_DEB_…" />
        </label>
        <QueryState isLoading={query.isLoading} error={query.error} empty={!query.data || query.data.items.length === 0}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Borrower</th><th>Province</th><th>Income</th><th>Outstanding</th><th>Risk</th><th>Root cause</th></tr></thead>
              <tbody>{query.data?.items.map((row) => (
                <tr key={row.borrower_id}>
                  <td>{row.borrower_id}</td><td>{row.province ?? "—"}</td>
                  <td>{formatMoney(row.monthly_income_idr)}</td><td>{formatMoney(row.total_loan_outstanding_idr)}</td>
                  <td>{row.risk_short ?? "—"}</td><td>{row.primary_default_root_cause ?? "—"}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </QueryState>
      </section>
    </>
  );
}

export function DecisionsPage() {
  const query = useQuery({ queryKey: ["decisions"], queryFn: ({ signal }) => getDecisions(50, 0, signal), retry: false });
  return (
    <>
      <PageHeader eyebrow="Decision management" title="Decisions" description="Immutable action-log records from PostgreSQL." />
      <QueryState isLoading={query.isLoading} error={query.error} empty={!query.data || query.data.items.length === 0}>
        <section className="panel table-wrap">
          <table><thead><tr><th>ID</th><th>Borrower</th><th>Action</th><th>Status</th><th>Rule</th><th>Created</th></tr></thead>
            <tbody>{query.data?.items.map((row) => <tr key={row.id}><td>{row.id}</td><td>{row.borrower_id}</td><td>{row.action_type}</td><td>{row.action_status}</td><td>{row.rule_code ?? "—"}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
        </section>
      </QueryState>
    </>
  );
}

export function PortfolioPage() {
  const query = useQuery({ queryKey: ["portfolio-summary"], queryFn: ({ signal }) => getPortfolioSummary(signal), retry: false });
  return (
    <>
      <PageHeader eyebrow="Portfolio analytics" title="Portfolio" description="Server-side portfolio aggregates." />
      <QueryState isLoading={query.isLoading} error={query.error} empty={!query.data}>
        {query.data && <div className="metric-grid">
          <section className="panel"><span className="eyebrow">Borrowers</span><h3>{query.data.total_borrowers}</h3></section>
          <section className="panel"><span className="eyebrow">Outstanding</span><h3>{formatMoney(query.data.outstanding_exposure)}</h3></section>
          <section className="panel"><span className="eyebrow">Average DTI</span><h3>{query.data.average_dti.toFixed(3)}</h3></section>
          <section className="panel"><span className="eyebrow">High-risk</span><h3>{query.data.high_risk_borrowers}</h3></section>
          <section className="panel"><span className="eyebrow">Defaulted</span><h3>{query.data.defaulted_borrowers}</h3></section>
        </div>}
      </QueryState>
    </>
  );
}

export function ModelsPage() {
  const query = useQuery({ queryKey: ["model-versions"], queryFn: ({ signal }) => getModels(signal), retry: false });
  return (
    <>
      <PageHeader eyebrow="Model intelligence" title="Model registry" description="Registered model versions and promotion metadata." />
      <QueryState isLoading={query.isLoading} error={query.error} empty={!query.data || query.data.items.length === 0}>
        <section className="panel table-wrap">
          <table><thead><tr><th>Task</th><th>Model</th><th>Version</th><th>Stage</th><th>Algorithm</th><th>Active</th></tr></thead>
            <tbody>{query.data?.items.map((row) => <tr key={row.id}><td>{row.task_name}</td><td>{row.model_name}</td><td>{row.version}</td><td>{row.stage}</td><td>{row.algorithm ?? "—"}</td><td>{row.is_active ? "Yes" : "No"}</td></tr>)}</tbody>
          </table>
        </section>
      </QueryState>
    </>
  );
}

export function AuditPage() {
  const query = useQuery({ queryKey: ["audit-events"], queryFn: ({ signal }) => getAuditEvents(100, signal), retry: false });
  return (
    <>
      <PageHeader eyebrow="Audit & governance" title="Audit events" description="Action, prediction, and drift records from the backend." />
      <QueryState isLoading={query.isLoading} error={query.error} empty={!query.data || query.data.items.length === 0}>
        <section className="panel table-wrap">
          <table><thead><tr><th>Time</th><th>Type</th><th>Borrower</th><th>Status</th></tr></thead>
            <tbody>{query.data?.items.map((row, index) => <tr key={`${row.occurred_at}-${index}`}><td>{new Date(row.occurred_at).toLocaleString()}</td><td>{row.event_type}</td><td>{row.borrower_id ?? "—"}</td><td>{row.status}</td></tr>)}</tbody>
          </table>
        </section>
      </QueryState>
    </>
  );
}
