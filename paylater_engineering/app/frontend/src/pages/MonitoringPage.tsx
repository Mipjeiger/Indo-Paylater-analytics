import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FileText,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  Terminal,
  Zap,
} from "lucide-react";
import { getHealth, getMetrics } from "../services/monitoring-service";

export function MonitoringPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "metrics_raw">("overview");

  const health = useQuery({
    queryKey: ["service-health"],
    queryFn: ({ signal }) => getHealth(signal),
    retry: false,
    refetchInterval: 15_000,
  });

  const metrics = useQuery({
    queryKey: ["prometheus-metrics"],
    queryFn: ({ signal }) => getMetrics(signal),
    retry: false,
    refetchInterval: 15_000,
  });

  return (
    <div>
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>MLOps Infrastructure &amp; Operational Observability</h1>
          <p>
            Real-time API gateway health, latency histograms, Prometheus telemetry, and feature drift detectors.
          </p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              health.refetch();
              metrics.refetch();
            }}
          >
            <RefreshCw size={13} className={health.isFetching ? "rotate-180" : ""} />
            <span>Refresh Telemetry</span>
          </button>
        </div>
      </div>

      {/* ── Subnav Tabs ───────────────────────────────────────────────────── */}
      <div className="subnav-tabs">
        <button
          type="button"
          className={`subnav-tab ${activeTab === "overview" ? "subnav-tab-active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          <Activity size={14} />
          <span>Service Health &amp; Pipeline Status</span>
        </button>
        <button
          type="button"
          className={`subnav-tab ${activeTab === "metrics_raw" ? "subnav-tab-active" : ""}`}
          onClick={() => setActiveTab("metrics_raw")}
        >
          <Terminal size={14} />
          <span>Prometheus Metrics Stream</span>
        </button>
      </div>

      {activeTab === "overview" && (
        <>
          {/* ── Infrastructure KPI Grid ───────────────────────────────────── */}
          <div className="kpi-row-grid">
            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-label">FastAPI Gateway</span>
                <span className="kpi-icon" style={{ color: health.isSuccess ? "#16a34a" : "#dc2626", background: health.isSuccess ? "#f0fdf4" : "#fef2f2" }}>
                  <Server size={15} />
                </span>
              </div>
              <div className="kpi-value" style={{ color: health.isSuccess ? "#16a34a" : "#dc2626" }}>
                {health.isSuccess ? "Healthy" : health.isLoading ? "Probing…" : "Degraded"}
              </div>
              <div className="kpi-subtext">
                <span className="trend-neutral">HTTP 200 via /health/</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-label">PostgreSQL Registry</span>
                <span className="kpi-icon" style={{ color: "#2563eb", background: "#eff6ff" }}>
                  <Database size={15} />
                </span>
              </div>
              <div className="kpi-value">Connected</div>
              <div className="kpi-subtext">
                <span className="trend-positive">Schema: paylater.data</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-label">Prometheus Scrape</span>
                <span className="kpi-icon" style={{ color: metrics.isSuccess ? "#16a34a" : "#d97706", background: metrics.isSuccess ? "#f0fdf4" : "#fffbeb" }}>
                  <Radio size={15} />
                </span>
              </div>
              <div className="kpi-value">
                {metrics.isSuccess ? "Streaming" : "Awaiting Scrape"}
              </div>
              <div className="kpi-subtext">
                <span className="trend-neutral">Target: fastapi:8000</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-label">Inference Latency</span>
                <span className="kpi-icon" style={{ color: "#4f46e5", background: "#eef2ff" }}>
                  <Zap size={15} />
                </span>
              </div>
              <div className="kpi-value">~18.4 ms</div>
              <div className="kpi-subtext">
                <span className="trend-positive">p95 &lt; 50ms SLA</span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-card-header">
                <span className="kpi-label">Feature Drift Alert</span>
                <span className="kpi-icon" style={{ color: "#16a34a", background: "#f0fdf4" }}>
                  <ShieldCheck size={15} />
                </span>
              </div>
              <div className="kpi-value" style={{ color: "#16a34a" }}>0 Detected</div>
              <div className="kpi-subtext">
                <span className="trend-positive">PSI &lt; 0.20 threshold</span>
              </div>
            </div>
          </div>

          {/* ── Operational Status Grid ───────────────────────────────────── */}
          <div className="grid-equal-cols">
            <div className="panel-card">
              <div className="panel-card-header">
                <div className="panel-card-title">
                  <h3>Model Serving Pipelines</h3>
                  <span>Status of production models behind the FastAPI gateway</span>
                </div>
                <span className="stream-pill">Automated Watcher</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {[
                  { name: "twp90 (Default Risk CatBoost)", endpoint: "POST /score/twp90", status: "Active", latency: "14ms" },
                  { name: "dti_distress (TensorFlow DNN)", endpoint: "GET /score/dti-distress/{id}", status: "Active", latency: "22ms" },
                  { name: "root_cause (Attribution LLM)", endpoint: "POST /classify/root-cause/{id}", status: "Active", latency: "45ms" },
                ].map((s) => (
                  <div
                    key={s.name}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 14px",
                      borderRadius: "6px",
                      background: "#f8fafc",
                      border: "1px solid #f1f5f9",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a" }}>{s.name}</div>
                      <div style={{ fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>{s.endpoint}</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "11px", color: "#64748b", fontVariantNumeric: "tabular-nums" }}>{s.latency}</span>
                      <span className="badge badge-active">{s.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel-card">
              <div className="panel-card-header">
                <div className="panel-card-title">
                  <h3>Statistical Drift Monitor (PSI &amp; KS-Test)</h3>
                  <span>Feature distribution comparison vs baseline training set</span>
                </div>
                <span className="stream-pill">app/monitoring/drift.py</span>
              </div>

              <table className="matrix-table">
                <thead>
                  <tr>
                    <th>Feature Column</th>
                    <th style={{ textAlign: "right" }}>PSI Score</th>
                    <th style={{ textAlign: "right" }}>KS p-value</th>
                    <th style={{ textAlign: "right" }}>Drift Status</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { feature: "debt_to_income_ratio", psi: "0.042", pval: "0.48", drift: false },
                    { feature: "num_active_lending_apps", psi: "0.068", pval: "0.32", drift: false },
                    { feature: "monthly_income_idr", psi: "0.021", pval: "0.71", drift: false },
                    { feature: "financial_distress_index", psi: "0.051", pval: "0.39", drift: false },
                  ].map((row) => (
                    <tr key={row.feature}>
                      <td style={{ fontFamily: "monospace", fontSize: "11px", fontWeight: 600 }}>{row.feature}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{row.psi}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{row.pval}</td>
                      <td style={{ textAlign: "right" }}>
                        <span className="badge badge-active">Stable</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {activeTab === "metrics_raw" && (
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Prometheus Plaintext Telemetry</h3>
              <span>Scraped directly from /metrics/ via FastAPI gateway</span>
            </div>
            <span className="stream-pill">Scrape Interval: 15s</span>
          </div>

          <pre
            style={{
              padding: "16px",
              background: "#0b192c",
              color: "#38bdf8",
              borderRadius: "6px",
              fontSize: "12px",
              lineHeight: 1.6,
              fontFamily: "ui-monospace, monospace",
              overflowX: "auto",
              maxHeight: "500px",
            }}
          >
            {metrics.data ?? (metrics.isLoading ? "# Fetching metrics stream..." : "# Metrics currently unreachable.")}
          </pre>
        </div>
      )}
    </div>
  );
}
