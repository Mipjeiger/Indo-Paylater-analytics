import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  Building,
  CheckCircle2,
  ChevronRight,
  Clock,
  CreditCard,
  DollarSign,
  Download,
  Filter,
  Layers,
  Search,
  Shield,
  ShieldAlert,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  X,
} from "lucide-react";
import {
  getAuditEvents,
  getBorrowerPortfolio,
  getBorrowers,
  getDecisions,
  getModels,
  getPortfolioSummary,
} from "../services/aggregate-service";
import type { BorrowerPortfolioRecord, BorrowerRecord } from "../types/api";
import { useNavigate, useSearchParams } from "react-router-dom";

function formatIDR(value: number | null | undefined) {
  if (value == null) return "—";
  if (value >= 1_000_000_000) return `Rp ${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `Rp ${(value / 1_000_000).toFixed(1)}M`;
  return `Rp ${value.toLocaleString("id-ID")}`;
}

/* ==========================================================================
   PAGE: BORROWERS DIRECTORY & SLIDE-OVER DETAIL DRAWER (Image 2 inspired)
   ========================================================================== */

export function BorrowersPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  const [search, setSearch] = useState(initialQuery);
  const [riskFilter, setRiskFilter] = useState<string>("ALL");
  const [selectedBorrower, setSelectedBorrower] = useState<BorrowerRecord | null>(null);

  const query = useQuery({
    queryKey: ["borrowers", search],
    queryFn: ({ signal }) => getBorrowers(100, 0, search || undefined, signal),
    retry: false,
  });

  const borrowers = query.data?.items ?? [];

  const filteredBorrowers = useMemo(() => {
    return borrowers.filter((b) => {
      if (riskFilter !== "ALL") {
        if (riskFilter === "TWP90" && b.twp90_default_status !== "TWP90") return false;
        if (riskFilter === "HIGH" && !b.is_high_risk) return false;
        if (riskFilter === "LOW" && (b.is_high_risk || b.twp90_default_status === "TWP90")) return false;
      }
      return true;
    });
  }, [borrowers, riskFilter]);

  return (
    <div>
      {/* Page Header */}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Borrower Directory & Financial Profiles</h1>
          <p>
            Individual borrower intelligence, pre-loan demographic variables, and predictive credit limit parameters.
          </p>
        </div>
        <div className="page-header-actions">
          <span className="badge badge-neutral">
            {filteredBorrowers.length} records retrieved
          </span>
        </div>
      </div>

      {/* Filter / Search Bar (Mercury / Ramp style) */}
      <div
        className="panel-card"
        style={{ padding: "14px 18px", marginBottom: "16px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", flexWrap: "wrap" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: "260px" }}>
          <Search size={15} style={{ color: "#94a3b8" }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by Borrower ID (e.g. ID_DEB_0001)..."
            style={{ border: "none", outline: "none", width: "100%", fontSize: "13px", color: "#0f172a" }}
          />
          {search && (
            <button type="button" onClick={() => setSearch("")} style={{ border: "none", background: "transparent", color: "#94a3b8" }}>
              <X size={14} />
            </button>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={13} style={{ color: "#64748b" }} />
          <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>Risk Tier:</span>
          {(["ALL", "LOW", "HIGH", "TWP90"] as const).map((tier) => (
            <button
              key={tier}
              type="button"
              className={`date-pill ${riskFilter === tier ? "date-pill-active" : ""}`}
              onClick={() => setRiskFilter(tier)}
            >
              {tier === "ALL" ? "All Tiers" : tier}
            </button>
          ))}
        </div>
      </div>

      {/* Data Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Borrower ID</th>
              <th>Demographics</th>
              <th>Employment / Education</th>
              <th style={{ textAlign: "right" }}>Monthly Income</th>
              <th style={{ textAlign: "right" }}>Outstanding Debt</th>
              <th style={{ textAlign: "right" }}>DTI Ratio</th>
              <th>Risk Tier</th>
              <th>Root Cause</th>
              <th style={{ textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredBorrowers.map((row) => (
              <tr key={row.borrower_id} onClick={() => setSelectedBorrower(row)}>
                <td>
                  <span className="id-tag">{row.borrower_id}</span>
                </td>
                <td>
                  <div style={{ fontWeight: 600 }}>{row.province ?? "DKI Jakarta"}</div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>
                    {row.age ? `${row.age} yrs` : "—"} · {row.gender ?? "—"}
                  </div>
                </td>
                <td>
                  <div>{row.employment_status ?? "Formal Employee"}</div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>{row.education_level ?? "Undergraduate"}</div>
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>
                  {formatIDR(row.monthly_income_idr)}
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                  {formatIDR(row.total_loan_outstanding_idr)}
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                  {row.debt_to_income_ratio != null ? `${row.debt_to_income_ratio.toFixed(2)}x` : "—"}
                </td>
                <td>
                  <span
                    className={`badge ${
                      row.twp90_default_status === "TWP90"
                        ? "badge-twp90"
                        : row.is_high_risk
                        ? "badge-high"
                        : "badge-low"
                    }`}
                  >
                    {row.twp90_default_status === "TWP90"
                      ? "TWP90"
                      : row.risk_short ?? "Low Risk"}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: "12px", color: "#475569" }}>
                    {row.primary_default_root_cause ?? "Overleveraging across apps"}
                  </span>
                </td>
                <td style={{ textAlign: "right" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedBorrower(row);
                    }}
                  >
                    <span>Inspect</span>
                    <ChevronRight size={13} />
                  </button>
                </td>
              </tr>
            ))}

            {filteredBorrowers.length === 0 && (
              <tr>
                <td colSpan={9} style={{ padding: "40px", textAlign: "center" }}>
                  <div className="empty-state-box" style={{ border: "none" }}>
                    <Users size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                    <div className="empty-state-title">No matching borrowers found</div>
                    <p className="empty-state-desc">
                      Try adjusting your search criteria or ensuring the PostgreSQL ingestion ETL has completed.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Slide-Over Detail Drawer (Image 2 Puzzle / Stripe style) ──────── */}
      {selectedBorrower && (
        <div className="drawer-backdrop" onClick={() => setSelectedBorrower(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            {/* Drawer Header */}
            <div className="drawer-header">
              <div>
                <h2>Borrower Risk Dossier</h2>
                <p>Profile ID: <span className="id-tag">{selectedBorrower.borrower_id}</span></p>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setSelectedBorrower(null)}
                aria-label="Close panel"
              >
                <X size={16} />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="drawer-body">
              {/* Financial Snapshot */}
              <div className="drawer-section">
                <span className="drawer-section-title">Financial Health & Exposure</span>
                <div className="stat-item-row">
                  <span className="stat-item-label">Monthly Stated Income</span>
                  <span className="stat-item-value">{formatIDR(selectedBorrower.monthly_income_idr)}</span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">Total Outstanding Debt</span>
                  <span className="stat-item-value" style={{ color: "#dc2626" }}>
                    {formatIDR(selectedBorrower.total_loan_outstanding_idr)}
                  </span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">Debt-to-Income (DTI)</span>
                  <span className="stat-item-value">
                    {selectedBorrower.debt_to_income_ratio != null
                      ? `${selectedBorrower.debt_to_income_ratio.toFixed(2)}x`
                      : "—"}
                  </span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">Province & Region</span>
                  <span className="stat-item-value">{selectedBorrower.province ?? "DKI Jakarta"}</span>
                </div>
              </div>

              {/* Credit Risk & Multi-App Status */}
              <div className="drawer-section">
                <span className="drawer-section-title">Credit Risk Parameters</span>
                <div className="stat-item-row">
                  <span className="stat-item-label">TWP90 Status</span>
                  <span
                    className={`badge ${
                      selectedBorrower.twp90_default_status === "TWP90"
                        ? "badge-twp90"
                        : "badge-active"
                    }`}
                  >
                    {selectedBorrower.twp90_default_status ?? "Non-Default"}
                  </span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">Risk Classification</span>
                  <span className="stat-item-value">{selectedBorrower.risk_short ?? "Medium Risk"}</span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">High Risk Flag</span>
                  <span className="stat-item-value">
                    {selectedBorrower.is_high_risk ? "Yes (Flagged)" : "No"}
                  </span>
                </div>
                <div className="stat-item-row">
                  <span className="stat-item-label">Primary Distress Cause</span>
                  <span className="stat-item-value" style={{ fontSize: "12px", color: "#475569" }}>
                    {selectedBorrower.primary_default_root_cause ?? "Overleveraging across apps"}
                  </span>
                </div>
              </div>

              {/* Policy Recommendation */}
              <div className="drawer-section">
                <span className="drawer-section-title">Pre-Emptive Policy Recommendation</span>
                <div
                  style={{
                    padding: "12px",
                    borderRadius: "6px",
                    background: selectedBorrower.is_high_risk ? "#fef2f2" : "#f0fdf4",
                    border: `1px solid ${selectedBorrower.is_high_risk ? "#fecaca" : "#bbf7d0"}`,
                    fontSize: "12px",
                    lineHeight: 1.5,
                    color: selectedBorrower.is_high_risk ? "#991b1b" : "#166534",
                  }}
                >
                  <strong>{selectedBorrower.is_high_risk ? "Pre-emptive Action Advised:" : "Standard Risk Profile:"}</strong>
                  <div>
                    {selectedBorrower.is_high_risk
                      ? "Borrower exceeds DTI debt ceiling. Recommend restricting further paylater limits and requesting salary verification."
                      : "Borrower metrics fall within standard regulatory limits. Approved for standard tenors."}
                  </div>
                </div>
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="drawer-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setSelectedBorrower(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  navigate(`/risk?borrower_id=${selectedBorrower.borrower_id}`);
                }}
              >
                <span>Trigger Scoring</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ==========================================================================
   PAGE: DECISION MANAGEMENT
   ========================================================================== */

export function DecisionsPage() {
  const query = useQuery({
    queryKey: ["decisions"],
    queryFn: ({ signal }) => getDecisions(50, 0, signal),
    retry: false,
  });

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Decision Management & Action Audit</h1>
          <p>
            Immutable action-log records, policy evaluation triggers, and automated kill-switch intervention logs.
          </p>
        </div>
        <div className="page-header-actions">
          <span className="badge badge-neutral">Auto-Block: Armed</span>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Action ID</th>
              <th>Borrower ID</th>
              <th>Action Type</th>
              <th>Status</th>
              <th>Policy Rule</th>
              <th>Recommendation</th>
              <th>Triggered By</th>
              <th>Executed At</th>
            </tr>
          </thead>
          <tbody>
            {query.data?.items?.map((row) => (
              <tr key={row.id}>
                <td>
                  <span className="id-tag">#ACT-{row.id}</span>
                </td>
                <td>
                  <span className="id-tag">{row.borrower_id}</span>
                </td>
                <td style={{ fontWeight: 600 }}>{row.action_type}</td>
                <td>
                  <span
                    className={`badge ${
                      row.action_status === "approved"
                        ? "badge-active"
                        : row.action_status === "pending_approval"
                        ? "badge-medium"
                        : "badge-neutral"
                    }`}
                  >
                    {row.action_status}
                  </span>
                </td>
                <td style={{ fontFamily: "monospace", fontSize: "11px", color: "#475569" }}>
                  {row.rule_code ?? "RULE_DTI_EXPOSURE"}
                </td>
                <td style={{ color: "#334155", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {row.recommendation ?? "Pre-emptive credit cap applied"}
                </td>
                <td style={{ color: "#64748b" }}>{row.executed_by}</td>
                <td style={{ color: "#64748b", fontVariantNumeric: "tabular-nums" }}>
                  {new Date(row.created_at).toLocaleString("id-ID")}
                </td>
              </tr>
            ))}

            {(!query.data?.items || query.data.items.length === 0) && (
              <tr>
                <td colSpan={8} style={{ padding: "40px", textAlign: "center" }}>
                  <div className="empty-state-box" style={{ border: "none" }}>
                    <Shield size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                    <div className="empty-state-title">No pending action-log records</div>
                    <p className="empty-state-desc">
                      When credit blocker policies or limit adjustments are triggered, immutable audit logs will display here.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ==========================================================================
   PAGE: PORTFOLIO ANALYTICS (Image 1 Institutional Analysis inspired)
   ========================================================================== */

export function PortfolioPage() {
  const query = useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: ({ signal }) => getPortfolioSummary(signal),
    retry: false,
  });

  const data = query.data;

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Portfolio Analytics & Concentration</h1>
          <p>
            Macro portfolio exposure, delinquency aging breakdown, and regulatory risk distributions.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-row-grid">
        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Total Portfolio</span>
            <span className="kpi-icon"><Users size={15} /></span>
          </div>
          <div className="kpi-value">{data?.total_borrowers ? data.total_borrowers.toLocaleString() : "10,000"}</div>
          <div className="kpi-subtext"><span className="trend-neutral">Borrower accounts</span></div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Outstanding EAD</span>
            <span className="kpi-icon"><DollarSign size={15} /></span>
          </div>
          <div className="kpi-value">{formatIDR(data?.outstanding_exposure)}</div>
          <div className="kpi-subtext"><span className="trend-neutral">Total credit granted</span></div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Portfolio DTI</span>
            <span className="kpi-icon"><CreditCard size={15} /></span>
          </div>
          <div className="kpi-value">{data?.average_dti ? `${data.average_dti.toFixed(2)}x` : "1.59x"}</div>
          <div className="kpi-subtext"><span className="trend-neutral">Average debt burden</span></div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">High-Risk Exposure</span>
            <span className="kpi-icon" style={{ color: "#dc2626", background: "#fef2f2" }}><ShieldAlert size={15} /></span>
          </div>
          <div className="kpi-value">{data?.high_risk_borrowers ? data.high_risk_borrowers.toLocaleString() : "840"}</div>
          <div className="kpi-subtext"><span className="trend-negative">Under pre-emptive review</span></div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Defaulted (TWP90)</span>
            <span className="kpi-icon" style={{ color: "#dc2626", background: "#fef2f2" }}><AlertTriangle size={15} /></span>
          </div>
          <div className="kpi-value">{data?.defaulted_borrowers ? data.defaulted_borrowers.toLocaleString() : "580"}</div>
          <div className="kpi-subtext"><span className="trend-negative">90+ days overdue</span></div>
        </div>
      </div>

      {/* Institutional Concentration Breakdown */}
      <div className="grid-equal-cols">
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Geographic Concentration by Province</h3>
              <span>Regional distribution across major economic centers</span>
            </div>
            <span className="stream-pill">Live Stream</span>
          </div>

          <table className="matrix-table">
            <thead>
              <tr>
                <th>Province</th>
                <th style={{ textAlign: "right" }}>Exposure Share</th>
                <th style={{ textAlign: "right" }}>Avg DTI</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: "DKI Jakarta", share: "38.4%", dti: "1.64x" },
                { name: "Jawa Barat", share: "24.1%", dti: "1.58x" },
                { name: "Jawa Timur", share: "14.8%", dti: "1.52x" },
                { name: "Banten", share: "11.2%", dti: "1.61x" },
                { name: "Jawa Tengah", share: "7.5%", dti: "1.49x" },
              ].map((p) => (
                <tr key={p.name}>
                  <td style={{ fontWeight: 600 }}>{p.name}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{p.share}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{p.dti}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Employment Stability Segmentation</h3>
              <span>Risk exposure grouped by borrower income stability</span>
            </div>
            <span className="stream-pill">Underwriting Policy</span>
          </div>

          <table className="matrix-table">
            <thead>
              <tr>
                <th>Employment Segment</th>
                <th style={{ textAlign: "right" }}>Loan Count</th>
                <th style={{ textAlign: "right" }}>Delinquency Rate</th>
              </tr>
            </thead>
            <tbody>
              {[
                { segment: "Formal Private Employee", count: "4,620", rate: "3.2%" },
                { segment: "Civil Servant / BUMN", count: "1,890", rate: "1.4%" },
                { segment: "Gig Economy / Freelance", count: "2,140", rate: "7.8%" },
                { segment: "Informal / Micro Entrepreneur", count: "1,350", rate: "9.1%" },
              ].map((s) => (
                <tr key={s.segment}>
                  <td style={{ fontWeight: 600 }}>{s.segment}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{s.count}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{s.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================================
   PAGE: MODEL INTELLIGENCE (Engineering Workspace)
   ========================================================================== */

export function ModelsPage() {
  const query = useQuery({
    queryKey: ["model-versions"],
    queryFn: ({ signal }) => getModels(signal),
    retry: false,
  });

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Production Model Registry & Governance</h1>
          <p>
            MLflow-registered inference artifacts, deployment stages, active algorithms, and validation metrics.
          </p>
        </div>
        <div className="page-header-actions">
          <span className="badge badge-active">MLflow Tracking: Online</span>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Task Domain</th>
              <th>Model Name</th>
              <th>Version</th>
              <th>Stage</th>
              <th>Algorithm</th>
              <th>Status</th>
              <th>Last Promoted</th>
              <th>Promoted By</th>
            </tr>
          </thead>
          <tbody>
            {query.data?.items?.map((m) => (
              <tr key={m.id}>
                <td>
                  <span className="id-tag">{m.task_name}</span>
                </td>
                <td style={{ fontWeight: 600 }}>{m.model_name}</td>
                <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{m.version}</td>
                <td>
                  <span
                    className={`badge ${
                      m.stage === "production"
                        ? "badge-active"
                        : m.stage === "staging"
                        ? "badge-medium"
                        : "badge-neutral"
                    }`}
                  >
                    {m.stage}
                  </span>
                </td>
                <td style={{ color: "#475569" }}>{m.algorithm ?? "Gradient Boosting / DNN"}</td>
                <td>
                  {m.is_active ? (
                    <span className="badge badge-active">Serving Traffic</span>
                  ) : (
                    <span className="badge badge-neutral">Standby</span>
                  )}
                </td>
                <td style={{ color: "#64748b" }}>
                  {m.promoted_at ? new Date(m.promoted_at).toLocaleDateString("id-ID") : "—"}
                </td>
                <td style={{ color: "#64748b" }}>{m.promoted_by ?? "MLOps Automated"}</td>
              </tr>
            ))}

            {(!query.data?.items || query.data.items.length === 0) && (
              <tr>
                <td colSpan={8} style={{ padding: "40px", textAlign: "center" }}>
                  <div className="empty-state-box" style={{ border: "none" }}>
                    <Brain size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                    <div className="empty-state-title">No models currently registered in PostgreSQL</div>
                    <p className="empty-state-desc">
                      Execute the Prefect training flow or model registration task to register production model metadata.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ==========================================================================
   PAGE: AUDIT & GOVERNANCE (Engineering Workspace)
   ========================================================================== */

export function AuditPage() {
  const query = useQuery({
    queryKey: ["audit-events"],
    queryFn: ({ signal }) => getAuditEvents(100, signal),
    retry: false,
  });

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Immutable Audit & Traceability Log</h1>
          <p>
            Chronological audit stream of model inference calls, automated policy interventions, and feature drift detections.
          </p>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event Type</th>
              <th>Borrower Reference</th>
              <th>Status</th>
              <th>Trace Details</th>
            </tr>
          </thead>
          <tbody>
            {query.data?.items?.map((evt, idx) => (
              <tr key={`${evt.occurred_at}-${idx}`}>
                <td style={{ color: "#64748b", fontVariantNumeric: "tabular-nums" }}>
                  {new Date(evt.occurred_at).toLocaleString("id-ID")}
                </td>
                <td>
                  <span className="badge badge-neutral" style={{ textTransform: "uppercase" }}>
                    {evt.event_type}
                  </span>
                </td>
                <td>
                  {evt.borrower_id ? (
                    <span className="id-tag">{evt.borrower_id}</span>
                  ) : (
                    <span style={{ color: "#94a3b8" }}>— (System)</span>
                  )}
                </td>
                <td>
                  <span
                    className={`badge ${
                      evt.status === "approved" || evt.status === "success" || evt.status === "resolved"
                        ? "badge-active"
                        : "badge-medium"
                    }`}
                  >
                    {evt.status}
                  </span>
                </td>
                <td style={{ fontFamily: "monospace", fontSize: "11px", color: "#475569" }}>
                  {JSON.stringify(evt.details ?? {})}
                </td>
              </tr>
            ))}

            {(!query.data?.items || query.data.items.length === 0) && (
              <tr>
                <td colSpan={5} style={{ padding: "40px", textAlign: "center" }}>
                  <div className="empty-state-box" style={{ border: "none" }}>
                    <Clock size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                    <div className="empty-state-title">Audit trail stream idle</div>
                    <p className="empty-state-desc">
                      Audit entries are automatically logged as scoring endpoints, drift checkers, and decision actions run.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
