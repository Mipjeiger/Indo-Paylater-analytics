import { useState } from "react";
import type { FormEvent } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Info,
  Layers,
  Play,
  RotateCcw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { assessTwp90, assessDti, classifyRootCause } from "../services/risk-service";
import { useSearchParams } from "react-router-dom";

type ModelTab = "twp90" | "dti_distress" | "root_cause";

export function RiskPage() {
  const [searchParams] = useSearchParams();
  const initialId = searchParams.get("borrower_id") ?? "ID_DEB_0001";

  const [activeTab, setActiveTab] = useState<ModelTab>("twp90");
  const [borrowerId, setBorrowerId] = useState(initialId);

  // Common features required across the models
  const [features, setFeatures] = useState({
    age: "24",
    monthly_income_idr: "6500000",
    regional_minimum_wage_umr_idr: "5067381",
    num_active_lending_apps: "3",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Results for each model
  const [twp90Result, setTwp90Result] = useState<{ default_probability: number; model_version?: string | null } | null>(null);
  const [dtiResult, setDtiResult] = useState<{ dti: number; financial_distress_index: number; model_version?: string | null } | null>(null);
  const [rootCauseResult, setRootCauseResult] = useState<{ root_cause: string; model_version?: string | null } | null>(null);

  async function handleScore(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const parsedFeatures = {
      age: Number(features.age),
      monthly_income_idr: Number(features.monthly_income_idr),
      regional_minimum_wage_umr_idr: Number(features.regional_minimum_wage_umr_idr),
      num_active_lending_apps: Number(features.num_active_lending_apps),
    };

    try {
      if (activeTab === "twp90") {
        const res = await assessTwp90({ borrower_id: borrowerId, features: parsedFeatures });
        setTwp90Result(res);
      } else if (activeTab === "dti_distress") {
        const res = await assessDti(borrowerId, parsedFeatures);
        setDtiResult(res);
      } else if (activeTab === "root_cause") {
        const res = await classifyRootCause(borrowerId, { borrower_id: borrowerId, features: parsedFeatures });
        setRootCauseResult(res);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Inference service unreachable";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Risk Intelligence & Model Inference</h1>
          <p>
            Real-time inference gateway for TWP90 default probability, deep learning DTI distress forecasting, and root-cause classification.
          </p>
        </div>
        <div className="page-header-actions">
          <span className="badge badge-active">Serving: MLflow &amp; Keras Engine</span>
        </div>
      </div>

      {/* ── Model Tabs (Ramp style) ───────────────────────────────────────── */}
      <div className="subnav-tabs">
        <button
          type="button"
          className={`subnav-tab ${activeTab === "twp90" ? "subnav-tab-active" : ""}`}
          onClick={() => { setActiveTab("twp90"); setError(null); }}
        >
          <ShieldAlert size={14} />
          <span>Task 1: TWP90 Default Risk</span>
        </button>
        <button
          type="button"
          className={`subnav-tab ${activeTab === "dti_distress" ? "subnav-tab-active" : ""}`}
          onClick={() => { setActiveTab("dti_distress"); setError(null); }}
        >
          <Cpu size={14} />
          <span>Task 2: Gen Z DTI &amp; Distress Forecasting</span>
        </button>
        <button
          type="button"
          className={`subnav-tab ${activeTab === "root_cause" ? "subnav-tab-active" : ""}`}
          onClick={() => { setActiveTab("root_cause"); setError(null); }}
        >
          <BrainCircuit size={14} />
          <span>Task 3: Root-Cause Classification</span>
        </button>
      </div>

      {/* ── Model Inference Interface Grid ───────────────────────────────── */}
      <div className="grid-two-cols">
        {/* Input Panel */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Inference Input Parameters</h3>
              <span>
                {activeTab === "twp90" && "Binary classification feature vector (CatBoost/LightGBM)"}
                {activeTab === "dti_distress" && "Continuous multi-target tensor inputs (TensorFlow DNN)"}
                {activeTab === "root_cause" && "Categorical & behavioral attribution variables"}
              </span>
            </div>
            <span className="stream-pill">FastAPI Gateway</span>
          </div>

          <form onSubmit={handleScore} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
              Borrower Reference ID
              <input
                required
                type="text"
                value={borrowerId}
                onChange={(e) => setBorrowerId(e.target.value)}
                placeholder="ID_DEB_0001"
                style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
              />
            </label>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Borrower Age (Years)
                <input
                  required
                  type="number"
                  value={features.age}
                  onChange={(e) => setFeatures({ ...features, age: e.target.value })}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Active Lending Apps
                <input
                  required
                  type="number"
                  value={features.num_active_lending_apps}
                  onChange={(e) => setFeatures({ ...features, num_active_lending_apps: e.target.value })}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Monthly Stated Income (IDR)
                <input
                  required
                  type="number"
                  value={features.monthly_income_idr}
                  onChange={(e) => setFeatures({ ...features, monthly_income_idr: e.target.value })}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Regional UMR Wage (IDR)
                <input
                  required
                  type="number"
                  value={features.regional_minimum_wage_umr_idr}
                  onChange={(e) => setFeatures({ ...features, regional_minimum_wage_umr_idr: e.target.value })}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>
            </div>

            {error && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "6px",
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  color: "#991b1b",
                  fontSize: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ width: "100%" }}
              >
                <Play size={14} />
                <span>{loading ? "Running Neural Inference…" : "Execute Prediction"}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Output Panel (Distinct predictions from verified outcomes) */}
        <div className="panel-card">
          <div className="panel-card-header">
            <div className="panel-card-title">
              <h3>Model Prediction Result</h3>
              <span>Strict separation: ML prediction vs. confirmed historical outcome</span>
            </div>
            <span className="badge badge-neutral">Inference Envelope</span>
          </div>

          {/* Model 1: TWP90 Output */}
          {activeTab === "twp90" && (
            <div>
              {twp90Result ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ padding: "20px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
                    <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                      Predicted Default Probability (TWP90)
                    </span>
                    <div style={{ fontSize: "40px", fontWeight: 800, color: twp90Result.default_probability > 0.5 ? "#dc2626" : "#16a34a", margin: "6px 0" }}>
                      {(twp90Result.default_probability * 100).toFixed(1)}%
                    </div>
                    <span
                      className={`badge ${
                        twp90Result.default_probability > 0.5 ? "badge-critical" : "badge-low"
                      }`}
                    >
                      {twp90Result.default_probability > 0.5 ? "HIGH TWP90 RISK" : "NORMAL REPAYMENT PROFILE"}
                    </span>
                  </div>

                  <div className="stat-item-row">
                    <span className="stat-item-label">Serving Model Version</span>
                    <span className="stat-item-value">{twp90Result.model_version ?? "twp90_production_v1"}</span>
                  </div>
                  <div className="stat-item-row">
                    <span className="stat-item-label">Algorithm</span>
                    <span className="stat-item-value">CatBoost Classifier (Early Stopping 50)</span>
                  </div>
                  <div className="stat-item-row">
                    <span className="stat-item-label">Underwriting Guideline</span>
                    <span className="stat-item-value" style={{ color: twp90Result.default_probability > 0.5 ? "#dc2626" : "#16a34a" }}>
                      {twp90Result.default_probability > 0.5 ? "Reject / Cap Limit to 0" : "Approve with Standard Limits"}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="empty-state-box">
                  <ShieldAlert size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                  <div className="empty-state-title">Awaiting TWP90 Inference Trigger</div>
                  <p className="empty-state-desc">
                    Submit the feature parameters to run the production scoring model against the FastAPI endpoint.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Model 2: DTI & Distress Output */}
          {activeTab === "dti_distress" && (
            <div>
              {dtiResult ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
                      <span style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                        Forecasted DTI Ratio
                      </span>
                      <div style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", margin: "6px 0" }}>
                        {dtiResult.dti.toFixed(2)}x
                      </div>
                      <span className="badge badge-medium">Target Continuous</span>
                    </div>

                    <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
                      <span style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                        Financial Distress Index
                      </span>
                      <div style={{ fontSize: "28px", fontWeight: 800, color: dtiResult.financial_distress_index > 5 ? "#dc2626" : "#2563eb", margin: "6px 0" }}>
                        {dtiResult.financial_distress_index.toFixed(2)}
                      </div>
                      <span className="badge badge-neutral">Range 0.0 - 10.0</span>
                    </div>
                  </div>

                  <div className="stat-item-row">
                    <span className="stat-item-label">Serving Model Version</span>
                    <span className="stat-item-value">{dtiResult.model_version ?? "keras_dti_distress_v2"}</span>
                  </div>
                  <div className="stat-item-row">
                    <span className="stat-item-label">Architecture</span>
                    <span className="stat-item-value">Multi-Output Deep Neural Net (R²: 0.982)</span>
                  </div>
                </div>
              ) : (
                <div className="empty-state-box">
                  <Cpu size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                  <div className="empty-state-title">Awaiting Deep Learning Regression</div>
                  <p className="empty-state-desc">
                    TensorFlow multi-output network forecasts both continuous Debt-to-Income and Financial Distress index.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Model 3: Root Cause Output */}
          {activeTab === "root_cause" && (
            <div>
              {rootCauseResult ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ padding: "16px", background: "#fef2f2", borderRadius: "8px", border: "1px solid #fecaca" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#991b1b", textTransform: "uppercase" }}>
                      Attributed Root Cause
                    </span>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#7f1d1d", marginTop: "4px" }}>
                      {rootCauseResult.root_cause}
                    </div>
                  </div>

                  <div className="stat-item-row">
                    <span className="stat-item-label">Classifier Engine</span>
                    <span className="stat-item-value">LLM Rationale / Decision Tree Ensemble</span>
                  </div>
                  <div className="stat-item-row">
                    <span className="stat-item-label">Model Version</span>
                    <span className="stat-item-value">{rootCauseResult.model_version ?? "root_cause_v1"}</span>
                  </div>
                </div>
              ) : (
                <div className="empty-state-box">
                  <BrainCircuit size={28} style={{ color: "#94a3b8", marginBottom: "8px" }} />
                  <div className="empty-state-title">Awaiting Behavioral Root-Cause Inference</div>
                  <p className="empty-state-desc">
                    Identifies primary psychological driver: Consumptive Overspending, App Multiplicity, or Income Disruption.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
