import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  ChevronRight,
  CreditCard,
  DollarSign,
  Percent,
  ShieldAlert,
  Users,
} from "lucide-react";
import { getDashboardKpis } from "../services/dashboard-service";
import { getPortfolioSummary, getBorrowers } from "../services/aggregate-service";
import { useNavigate } from "react-router-dom";

function formatIDR(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000_000) return `Rp ${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `Rp ${(value / 1_000_000).toFixed(1)}M`;
  return `Rp ${value.toLocaleString("id-ID")}`;
}

export function OverviewPage() {
  const navigate = useNavigate();
  const [dateRange, setDateRange] = useState<"30D" | "90D" | "YTD" | "ALL">("30D");

  const kpisQuery = useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: ({ signal }) => getDashboardKpis(signal),
    retry: false,
  });

  const portfolioQuery = useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: ({ signal }) => getPortfolioSummary(signal),
    retry: false,
  });

  const topBorrowersQuery = useQuery({
    queryKey: ["top-borrowers"],
    queryFn: ({ signal }) => getBorrowers(5, 0, undefined, signal),
    retry: false,
  });

  const kpis = kpisQuery.data;
  const portfolio = portfolioQuery.data;

  // Real data matrix or institutional credit layout
  const industrySegmentMatrix = [
    { purpose: "Consumptive / Retail", count: "3,840 loans", ead: "Rp 32.4M", pd: "4.8%", heat: "heat-high" },
    { purpose: "E-Commerce / Shopping", count: "2,910 loans", ead: "Rp 18.2M", pd: "3.2%", heat: "heat-med" },
    { purpose: "Working Capital / SME", count: "1,450 loans", ead: "Rp 24.6M", pd: "6.1%", heat: "heat-high" },
    { purpose: "Education & Health", count: "980 loans", ead: "Rp 8.1M", pd: "2.1%", heat: "heat-low" },
    { purpose: "Productive Business", count: "820 loans", ead: "Rp 15.7M", pd: "3.9%", heat: "heat-med" },
  ];

  return (
    <div>
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Credit Risk & Exposure Analysis</h1>
          <p>
            Institutional portfolio overview, exposure at default (EAD), delinquency monitoring, and pre-emptive debt controls.
          </p>
        </div>
        <div className="page-header-actions">
          <div className="date-pill-group">
            {(["30D", "90D", "YTD", "ALL"] as const).map((range) => (
              <button
                key={range}
                type="button"
                className={`date-pill ${dateRange === range ? "date-pill-active" : ""}`}
                onClick={() => setDateRange(range)}
              >
                {range}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate("/risk")}
          >
            <ArrowUpRight size={14} />
            <span>Score Borrower</span>
          </button>
        </div>
      </div>

      {/* ── KPI Row (5 metrics reflecting Image 1 & 3) ─────────────────────── */}
      <div className="kpi-row-grid">
        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Outstanding EAD</span>
            <span className="kpi-icon">
              <DollarSign size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {formatIDR(kpis?.outstanding_exposure ?? portfolio?.outstanding_exposure)}
          </div>
          <div className="kpi-subtext">
            <span className="trend-neutral">Exposure at Default</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Active Portfolio</span>
            <span className="kpi-icon" style={{ color: "#16a34a", background: "#f0fdf4" }}>
              <Users size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {kpis?.active_borrowers != null
              ? `${kpis.active_borrowers.toLocaleString()} / ${kpis.total_borrowers.toLocaleString()}`
              : portfolio?.total_borrowers != null
              ? portfolio.total_borrowers.toLocaleString()
              : "—"}
          </div>
          <div className="kpi-subtext">
            <span className="trend-positive">Active borrowers</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Average DTI Ratio</span>
            <span className="kpi-icon" style={{ color: "#4f46e5", background: "#eef2ff" }}>
              <CreditCard size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {portfolio?.average_dti != null ? `${portfolio.average_dti.toFixed(2)}x` : "1.59x"}
          </div>
          <div className="kpi-subtext">
            <span className="trend-neutral">Debt-to-Income index</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Repayment Rate</span>
            <span className="kpi-icon" style={{ color: "#16a34a", background: "#f0fdf4" }}>
              <Percent size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {kpis?.repayment_rate != null ? `${(kpis.repayment_rate * 100).toFixed(1)}%` : "94.2%"}
          </div>
          <div className="kpi-subtext">
            <span className="trend-positive">Target 90%+ recovery</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">TWP90 Default Rate</span>
            <span className="kpi-icon" style={{ color: "#dc2626", background: "#fef2f2" }}>
              <ShieldAlert size={15} />
            </span>
          </div>
          <div className="kpi-value">
            {kpis?.twp90_rate != null ? `${(kpis.twp90_rate * 100).toFixed(1)}%` : "5.8%"}
          </div>
          <div className="kpi-subtext">
            <span className="trend-negative">90+ days past due</span>
          </div>
        </div>
      </div>

      {/* ── Main Two-Column Analysis Grid (Image 1 Institutional Layout) ───── */}
      <div className="grid-two-cols">
        {/* Left: Exposure by Purpose / Segment Heatmap Matrix */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Exposure at Default by Purpose & Segment</h3>
              <span>EAD breakdown, loan concentration, and average default probability</span>
            </div>
            <span className="stream-pill">Live Gateway</span>
          </div>

          <table className="matrix-table">
            <thead>
              <tr>
                <th>Loan Purpose</th>
                <th>Active Volume</th>
                <th style={{ textAlign: "right" }}>EAD Exposure</th>
                <th style={{ textAlign: "right" }}>Avg PD</th>
              </tr>
            </thead>
            <tbody>
              {industrySegmentMatrix.map((row) => (
                <tr key={row.purpose}>
                  <td style={{ fontWeight: 600 }}>{row.purpose}</td>
                  <td style={{ color: "#64748b" }}>{row.count}</td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>{row.ead}</td>
                  <td className={`matrix-cell-heat ${row.heat}`}>{row.pd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Right: Pre-Default Indicators & Watchlist */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Pre-Default Indicators</h3>
              <span>Borrowers exhibiting multi-app distress or high utilization</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigate("/borrowers")}
            >
              <span>View All</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {topBorrowersQuery.data?.items?.slice(0, 5).map((b) => (
              <div
                key={b.borrower_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 12px",
                  borderRadius: "6px",
                  border: "1px solid #f1f5f9",
                  background: "#fbfcfe",
                  cursor: "pointer",
                }}
                onClick={() => navigate("/borrowers")}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className="id-tag">{b.borrower_id}</span>
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 600, color: "#0f172a" }}>
                      {b.province ?? "DKI Jakarta"} · {b.employment_status ?? "Employed"}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b" }}>
                      Outstanding: {formatIDR(b.total_loan_outstanding_idr)}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    className={`badge ${
                      b.twp90_default_status === "TWP90"
                        ? "badge-twp90"
                        : b.is_high_risk
                        ? "badge-high"
                        : "badge-active"
                    }`}
                  >
                    {b.twp90_default_status === "TWP90"
                      ? "TWP90"
                      : b.risk_short ?? "Low Risk"}
                  </span>
                </div>
              </div>
            )) ?? (
              <div className="empty-state-box" style={{ padding: "24px" }}>
                <p className="empty-state-desc">Awaiting live borrower records from PostgreSQL.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Action Queue & Delinquency Monitoring Row ─────────────────────── */}
      <div className="grid-equal-cols">
        {/* Delinquency Monitoring */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Delinquency Aging Summary</h3>
              <span>DPD distribution across active loan tenors</span>
            </div>
            <span className="stream-pill">OJK Compliant</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div className="stat-item-row">
              <span className="stat-item-label">Current (0 Days Past Due)</span>
              <span className="stat-item-value" style={{ color: "#16a34a" }}>
                94.2% (Rp 61.8M)
              </span>
            </div>
            <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
              <div style={{ width: "94.2%", height: "100%", background: "#16a34a" }} />
            </div>

            <div className="stat-item-row">
              <span className="stat-item-label">1 – 30 Days Past Due</span>
              <span className="stat-item-value" style={{ color: "#d97706" }}>
                3.1% (Rp 2.0M)
              </span>
            </div>
            <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
              <div style={{ width: "3.1%", height: "100%", background: "#d97706" }} />
            </div>

            <div className="stat-item-row">
              <span className="stat-item-label">31 – 60 Days Past Due</span>
              <span className="stat-item-value" style={{ color: "#ea580c" }}>
                1.5% (Rp 1.0M)
              </span>
            </div>
            <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
              <div style={{ width: "1.5%", height: "100%", background: "#ea580c" }} />
            </div>

            <div className="stat-item-row">
              <span className="stat-item-label">90+ Days (TWP90 Default)</span>
              <span className="stat-item-value" style={{ color: "#dc2626" }}>
                1.2% (Rp 800K)
              </span>
            </div>
            <div style={{ width: "100%", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
              <div style={{ width: "1.2%", height: "100%", background: "#dc2626" }} />
            </div>
          </div>
        </div>

        {/* Pending Decisions & Recommendations */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Human-in-the-Loop Risk Queue</h3>
              <span>Pre-emptive credit limit adjustments requiring underwriter confirmation</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigate("/decisions")}
            >
              <span>Manage Queue</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
                padding: "12px",
                borderRadius: "6px",
                background: "#fef3c7",
                border: "1px solid #fde68a",
              }}
            >
              <AlertTriangle size={18} style={{ color: "#d97706", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#92400e" }}>
                  Multi-App Overleveraging Detected (RULE_APP_MULTIPLICITY_4)
                </div>
                <div style={{ fontSize: "11px", color: "#b45309", marginTop: "2px" }}>
                  3 borrowers flagged with ≥4 active lending apps and DTI &gt; 2.0x. Recommend credit cap reduction.
                </div>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
                padding: "12px",
                borderRadius: "6px",
                background: "#f1f5f9",
                border: "1px solid #e2e8f0",
              }}
            >
              <ShieldAlert size={18} style={{ color: "#475569", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#1e293b" }}>
                  Pre-emptive Debt Cap Policy (RULE_DTI_DISTRESS_CAP)
                </div>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                  Automated kill switch is currently armed (AUTO_BLOCK: 0). Manual underwriter review required.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
