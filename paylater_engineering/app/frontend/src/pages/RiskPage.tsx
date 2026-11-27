import { useState, useEffect } from "react";
import type { FormEvent } from "react";
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  FlaskConical,
  Play,
  RotateCcw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { assessTwp90, assessDti, classifyRootCause } from "../services/risk-service";
import { getBorrowerPortfolio } from "../services/aggregate-service";
import { useSearchParams } from "react-router-dom";

type ModelTab = "twp90" | "dti_distress" | "root_cause";

// ── Feature Typing ──────────────────────────────────────────────────────
type NumericField =
  | "age"
  | "monthly_income_idr"
  | "regional_minimum_wage_umr_idr"
  | "num_active_lending_apps"
  | "total_loan_outstanding_idr"
  | "credit_limit_granted_idr"
  | "loan_tenor_months"
  | "daily_interest_rate_pct"
  | "income_to_umr_ratio"
  | "credit_limit_utilization_ratio"
  | "monthly_installment_estimate_idr"
  | "debt_service_ratio"
  | "disposable_income_after_debt_idr"
  | "debt_to_income_ratio"
  | "financial_distress_index";

type StringFeatureField =
  | "gender"
  | "province"
  | "education_level"
  | "employment_status"
  | "primary_loan_purpose";

type Features = Record<NumericField, number | ""> & Record<StringFeatureField, string>;

const PROVINCE_OPTIONS = [
  "Bali", "Banten", "DI Yogyakarta", "DKI Jakarta", "Jawa Barat",
  "Jawa Tengah", "Jawa Timur", "Kalimantan Timur", "Lampung", "Riau",
  "Sulawesi Selatan", "Sumatera Utara",
];

const EDUCATION_OPTIONS = [
  "High School / SMK", "Diploma (D3)", "Bachelor (S1)", "Master (S2)",
];

const EMPLOYMENT_OPTIONS = [
  "Civil Servant / BUMN", "Digital Freelancer / Creator", "Entry-Level / Jobseeker",
  "Formal Private Employee", "Gig Worker / Ojol", "Micro-Entrepreneur / UMKM",
];

const PURPOSE_OPTIONS = [
  "Daily Living & Emergency Buffer", "Debt Refinancing / Gali Lubang",
  "Gadget & Electronics Paylater", "Lifestyle, Concert & FOMO Travel",
  "Micro-Business Working Capital", "Online Gambling / Speculative Trading",
];

const EMPTY_FEATURES: Features = {
  age: "", monthly_income_idr: "", regional_minimum_wage_umr_idr: "",
  num_active_lending_apps: "", gender: "", province: "", education_level: "",
  employment_status: "", primary_loan_purpose: "", total_loan_outstanding_idr: "",
  credit_limit_granted_idr: "", loan_tenor_months: "", daily_interest_rate_pct: "",
  income_to_umr_ratio: "", credit_limit_utilization_ratio: "",
  monthly_installment_estimate_idr: "", debt_service_ratio: "",
  disposable_income_after_debt_idr: "",
  debt_to_income_ratio: "", financial_distress_index: "",
};

// The minimal required fields per tab (The "Primary 5")
const CRITICAL_BY_TAB: Record<ModelTab, (keyof Features)[]> = {
  twp90: ["age", "monthly_income_idr", "regional_minimum_wage_umr_idr", "num_active_lending_apps"],
  dti_distress: ["monthly_income_idr", "total_loan_outstanding_idr", "monthly_installment_estimate_idr"],
  root_cause: ["monthly_income_idr", "num_active_lending_apps", "total_loan_outstanding_idr"],
};

function toNumericInput(raw: string): number | "" {
  const trimmed = raw.trim();
  if (trimmed === "" || trimmed === "-" || trimmed === ".") return "";
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : "";
}

/**
 * Builds the payload. Only includes critical fields + any other fields
 * the user actually filled in. The backend fills the rest with safe defaults.
 */
function buildPayload(input: Features, tab: ModelTab): Record<string, number | string> {
  const critical = CRITICAL_BY_TAB[tab];
  const missing: string[] = [];
  const payload: Record<string, number | string> = {};

  // 1. Validate and include critical fields
  for (const k of critical) {
    const v = input[k];
    if (v === "" || v === undefined || v === null) {
      missing.push(k.replace(/_/g, " "));
    } else {
      payload[k] = v;
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Please provide required fields: ${missing.join(", ")}. (Advanced fields are optional).`
    );
  }

  // 2. Include any other fields that the user filled in
  const numericFields: NumericField[] = [
    "age", "num_active_lending_apps", "loan_tenor_months", "monthly_income_idr",
    "regional_minimum_wage_umr_idr", "total_loan_outstanding_idr", "credit_limit_granted_idr",
    "daily_interest_rate_pct", "income_to_umr_ratio", "credit_limit_utilization_ratio",
    "monthly_installment_estimate_idr", "debt_service_ratio", "disposable_income_after_debt_idr",
    "debt_to_income_ratio", "financial_distress_index",
  ];
  const stringFields: StringFeatureField[] = [
    "gender", "province", "education_level", "employment_status", "primary_loan_purpose",
  ];

  for (const k of numericFields) {
    if (!critical.includes(k) && input[k] !== "") {
      payload[k] = input[k];
    }
  }
  for (const k of stringFields) {
    if (!critical.includes(k) && input[k]?.trim() !== "") {
      payload[k] = input[k].trim();
    }
  }

  return payload;
}

export function RiskPage() {
  const [searchParams] = useSearchParams();
  const initialId = searchParams.get("borrower_id") ?? "";

  const [activeTab, setActiveTab] = useState<ModelTab>("twp90");
  const [borrowerId, setBorrowerId] = useState(initialId);

  const [features, setFeatures] = useState<Features>(EMPTY_FEATURES);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [loading, setLoading] = useState(false);
  const [fetchingProfile, setFetchingProfile] = useState(false);
  const [profileStatus, setProfileStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [twp90Result, setTwp90Result] = useState<{ default_probability: number; model_version?: string | null; defaulted_fields?: string[] } | null>(null);
  const [dtiResult, setDtiResult] = useState<{ dti: number; financial_distress_index: number; model_version?: string | null; defaulted_fields?: string[] } | null>(null);
  const [rootCauseResult, setRootCauseResult] = useState<{ root_cause: string; model_version?: string | null; defaulted_fields?: string[] } | null>(null);

  useEffect(() => {
    if (initialId.trim()) {
      fetchBorrowerData(initialId.trim());
    }
  }, [initialId]); // eslint-disable-line react-hooks/exhaustive-deps

  function updateIncomeOrUmr(income: number | "", umr: number | "") {
    setFeatures((prev) => {
      const next = { ...prev, monthly_income_idr: income, regional_minimum_wage_umr_idr: umr };
      if (typeof income === "number" && typeof umr === "number" && umr > 0) {
        next.income_to_umr_ratio = Number((income / umr).toFixed(2));
      }
      if (typeof income === "number" && typeof next.monthly_installment_estimate_idr === "number" && income > 0) {
        next.debt_service_ratio = Number((next.monthly_installment_estimate_idr / income).toFixed(3));
        next.disposable_income_after_debt_idr = income - next.monthly_installment_estimate_idr;
      }
      if (typeof income === "number" && typeof next.total_loan_outstanding_idr === "number" && income > 0) {
        next.debt_to_income_ratio = Number((next.total_loan_outstanding_idr / income).toFixed(3));
      }
      return next;
    });
  }

  function updateOutstandingOrLimit(outstanding: number | "", limit: number | "") {
    setFeatures((prev) => {
      const next = { ...prev, total_loan_outstanding_idr: outstanding, credit_limit_granted_idr: limit };
      if (typeof outstanding === "number" && typeof limit === "number" && limit > 0) {
        next.credit_limit_utilization_ratio = Number((outstanding / limit).toFixed(4));
      }
      if (typeof outstanding === "number" && typeof next.monthly_income_idr === "number" && next.monthly_income_idr > 0) {
        next.debt_to_income_ratio = Number((outstanding / next.monthly_income_idr).toFixed(3));
      }
      return next;
    });
  }

  async function fetchBorrowerData(id: string) {
    const cleanId = id.trim();
    if (!cleanId) {
      setProfileStatus("⚠️ Please enter a Borrower Reference ID.");
      return;
    }

    setFetchingProfile(true);
    setProfileStatus(null);
    setError(null);
    try {
      const data = await getBorrowerPortfolio(cleanId);
      if (data) {
        const income = data.monthly_income_idr ?? "";
        const umr = data.regional_minimum_wage_umr_idr ?? "";
        const outstanding = data.total_loan_outstanding_idr ?? "";
        const limit = data.credit_limit_granted_idr ?? "";
        const installment = data.monthly_installment_estimate_idr ?? "";

        setFeatures({
          age: data.age ?? "",
          gender: data.gender ?? "",
          province: data.province ?? "",
          education_level: data.education_level ?? "",
          employment_status: data.employment_status ?? "",
          monthly_income_idr: income,
          regional_minimum_wage_umr_idr: umr,
          num_active_lending_apps: data.num_active_lending_apps ?? "",
          total_loan_outstanding_idr: outstanding,
          credit_limit_granted_idr: limit,
          loan_tenor_months: data.loan_tenor_months ?? "",
          daily_interest_rate_pct: data.daily_interest_rate_pct ?? "",
          primary_loan_purpose: data.primary_loan_purpose ?? "",
          income_to_umr_ratio: data.income_to_umr_ratio ?? (typeof income === "number" && typeof umr === "number" && umr > 0 ? Number((income / umr).toFixed(2)) : ""),
          credit_limit_utilization_ratio: data.credit_limit_utilization_ratio ?? (typeof outstanding === "number" && typeof limit === "number" && limit > 0 ? Number((outstanding / limit).toFixed(4)) : ""),
          monthly_installment_estimate_idr: installment,
          debt_service_ratio: data.debt_service_ratio ?? (typeof income === "number" && typeof installment === "number" && income > 0 ? Number((installment / income).toFixed(3)) : ""),
          disposable_income_after_debt_idr: data.disposable_income_after_debt_idr ?? (typeof income === "number" && typeof installment === "number" ? income - installment : ""),
          debt_to_income_ratio: data.debt_to_income_ratio ?? (typeof income === "number" && typeof outstanding === "number" && income > 0 ? Number((outstanding / income).toFixed(3)) : ""),
          financial_distress_index: data.financial_distress_index ?? "",
        });
        setProfileStatus(`✓ Loaded record for ${cleanId} from secure database`);
      }
    } catch {
      setProfileStatus(`⚠️ "${cleanId}" not found in database. Enter values manually or load synthetic benchmark.`);
    } finally {
      setFetchingProfile(false);
    }
  }

  async function loadSyntheticBenchmark() {
    setProfileStatus(null);
    setError(null);
    try {
      // Fetch from secure backend endpoint instead of hardcoded frontend object
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/benchmark`);
      if (!res.ok) throw new Error(`Benchmark fetch failed: ${res.status}`);
      const data = await res.json();
      
      setBorrowerId(data.borrower_id);
      setFeatures(data.features as Features);
      setProfileStatus(`ℹ️ Loaded ${data.source} scenario (${data.note})`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load benchmark scenario");
    }
  }

  function handleReset() {
    setBorrowerId("");
    setFeatures(EMPTY_FEATURES);
    setProfileStatus(null);
    setError(null);
    setTwp90Result(null);
    setDtiResult(null);
    setRootCauseResult(null);
  }

  async function handleScore(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    let payload: Record<string, number | string>;
    try {
      payload = buildPayload(features, activeTab);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid input parameters");
      setLoading(false);
      return;
    }

    try {
      if (activeTab === "twp90") {
        const res = await assessTwp90({ borrower_id: borrowerId || "ANONYMOUS_SIM", features: payload });
        setTwp90Result(res);
      } else if (activeTab === "dti_distress") {
        const res = await assessDti(borrowerId || "ANONYMOUS_SIM", payload);
        setDtiResult(res);
      } else if (activeTab === "root_cause") {
        const res = await classifyRootCause(borrowerId || "ANONYMOUS_SIM", { borrower_id: borrowerId || "ANONYMOUS_SIM", features: payload });
        setRootCauseResult(res);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err
        ? String((err as { message: string }).message)
        : "Inference service unreachable";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Risk Intelligence &amp; Model Inference</h1>
          <p>
            Real-time inference gateway for TWP90 default probability, deep learning DTI distress forecasting, and root-cause classification.
          </p>
        </div>
        <div className="page-header-actions" style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={loadSyntheticBenchmark}
            style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "5px" }}
            title="Load non-PII test vector for scenario simulation"
          >
            <FlaskConical size={13} />
            <span>Load Benchmark Scenario</span>
          </button>
          <span className="badge badge-active">Serving: MLflow &amp; Keras Engine</span>
        </div>
      </div>

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
            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                  Borrower Reference ID
                </span>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => fetchBorrowerData(borrowerId)}
                    disabled={fetchingProfile || !borrowerId.trim()}
                    style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "none", border: "none", color: "#2563eb", fontSize: "11px", fontWeight: 600, cursor: "pointer", padding: 0 }}
                  >
                    <Search size={12} />
                    <span>{fetchingProfile ? "Fetching…" : "Autofill from Database"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleReset}
                    style={{ display: "inline-flex", alignItems: "center", gap: "3px", background: "none", border: "none", color: "#94a3b8", fontSize: "11px", cursor: "pointer", padding: 0 }}
                  >
                    <RotateCcw size={11} />
                    <span>Clear</span>
                  </button>
                </div>
              </div>

              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  value={borrowerId}
                  onChange={(e) => setBorrowerId(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); fetchBorrowerData(borrowerId); } }}
                  placeholder="e.g. ID_DEB_1438774631 or leave blank for ad-hoc simulation"
                  style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => fetchBorrowerData(borrowerId)}
                  disabled={fetchingProfile || !borrowerId.trim()}
                  style={{ padding: "0 12px", height: "35px" }}
                >
                  <Database size={13} />
                </button>
              </div>

              {profileStatus && (
                <div style={{ fontSize: "11px", color: profileStatus.startsWith("✓") ? "#16a34a" : profileStatus.startsWith("ℹ") ? "#2563eb" : "#64748b", display: "flex", alignItems: "center", gap: "4px", marginTop: "2px" }}>
                  {profileStatus.startsWith("✓") && <CheckCircle2 size={12} />}
                  <span>{profileStatus}</span>
                </div>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Borrower Age (Years) {CRITICAL_BY_TAB[activeTab].includes("age") && <span style={{color:"#dc2626"}}>*</span>}
                <input
                  type="number" min={17} max={99} step={1} placeholder="e.g. 24"
                  value={features.age}
                  onChange={(e) => setFeatures((prev) => ({ ...prev, age: toNumericInput(e.target.value) }))}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Active Lending Apps {CRITICAL_BY_TAB[activeTab].includes("num_active_lending_apps") && <span style={{color:"#dc2626"}}>*</span>}
                <input
                  type="number" min={0} max={50} step={1} placeholder="e.g. 2"
                  value={features.num_active_lending_apps}
                  onChange={(e) => setFeatures((prev) => ({ ...prev, num_active_lending_apps: toNumericInput(e.target.value) }))}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Monthly Stated Income (IDR) {CRITICAL_BY_TAB[activeTab].includes("monthly_income_idr") && <span style={{color:"#dc2626"}}>*</span>}
                <input
                  type="number" min={0} placeholder="e.g. 5,000,000"
                  value={features.monthly_income_idr}
                  onChange={(e) => updateIncomeOrUmr(toNumericInput(e.target.value), features.regional_minimum_wage_umr_idr)}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "5px", fontSize: "12px", fontWeight: 600, color: "#334155" }}>
                Regional UMR Wage (IDR) {CRITICAL_BY_TAB[activeTab].includes("regional_minimum_wage_umr_idr") && <span style={{color:"#dc2626"}}>*</span>}
                <input
                  type="number" min={0} placeholder="e.g. 5,067,381"
                  value={features.regional_minimum_wage_umr_idr}
                  onChange={(e) => updateIncomeOrUmr(features.monthly_income_idr, toNumericInput(e.target.value))}
                  style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
                />
              </label>
            </div>

            {/* Expandable Advanced 18-Feature Configuration */}
            <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "8px" }}>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "6px", fontSize: "12px", fontWeight: 600, color: "#475569", cursor: "pointer" }}
              >
                <span>Full Feature Vector &amp; Scenario Simulator ({showAdvanced ? "Active" : "14 Additional Variables"})</span>
                {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showAdvanced && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                    Demographics &amp; Employment Profile
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Gender
                      <select value={features.gender} onChange={(e) => setFeatures((p) => ({ ...p, gender: e.target.value }))} style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}>
                        <option value="">Select Gender…</option>
                        <option value="Female">Female</option>
                        <option value="Male">Male</option>
                      </select>
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Province
                      <select value={features.province} onChange={(e) => setFeatures((p) => ({ ...p, province: e.target.value }))} style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}>
                        <option value="">Select Province…</option>
                        {PROVINCE_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Education Level
                      <select value={features.education_level} onChange={(e) => setFeatures((p) => ({ ...p, education_level: e.target.value }))} style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}>
                        <option value="">Select Education…</option>
                        {EDUCATION_OPTIONS.map((ed) => <option key={ed} value={ed}>{ed}</option>)}
                      </select>
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Employment Status
                      <select value={features.employment_status} onChange={(e) => setFeatures((p) => ({ ...p, employment_status: e.target.value }))} style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}>
                        <option value="">Select Employment…</option>
                        {EMPLOYMENT_OPTIONS.map((emp) => <option key={emp} value={emp}>{emp}</option>)}
                      </select>
                    </label>
                  </div>

                  <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                    Primary Loan Purpose
                    <select value={features.primary_loan_purpose} onChange={(e) => setFeatures((p) => ({ ...p, primary_loan_purpose: e.target.value }))} style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}>
                      <option value="">Select Purpose…</option>
                      {PURPOSE_OPTIONS.map((pur) => <option key={pur} value={pur}>{pur}</option>)}
                    </select>
                  </label>

                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginTop: "6px" }}>
                    Loan Facilities &amp; Exposure
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Total Outstanding (IDR) {CRITICAL_BY_TAB[activeTab].includes("total_loan_outstanding_idr") && <span style={{color:"#dc2626"}}>*</span>}
                      <input
                        type="number" placeholder="e.g. 3,500,000"
                        value={features.total_loan_outstanding_idr}
                        onChange={(e) => updateOutstandingOrLimit(toNumericInput(e.target.value), features.credit_limit_granted_idr)}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Credit Limit Granted (IDR)
                      <input
                        type="number" placeholder="e.g. 10,000,000"
                        value={features.credit_limit_granted_idr}
                        onChange={(e) => updateOutstandingOrLimit(features.total_loan_outstanding_idr, toNumericInput(e.target.value))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Loan Tenor (Months)
                      <input
                        type="number" step={1} placeholder="e.g. 6"
                        value={features.loan_tenor_months}
                        onChange={(e) => setFeatures((p) => ({ ...p, loan_tenor_months: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Daily Interest Rate (%)
                      <input
                        type="number" step="0.01" placeholder="e.g. 0.10"
                        value={features.daily_interest_rate_pct}
                        onChange={(e) => setFeatures((p) => ({ ...p, daily_interest_rate_pct: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>
                  </div>

                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginTop: "6px" }}>
                    Derived Capacity &amp; Utilization Ratios (Auto-Computed)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Income-to-UMR Ratio
                      <input
                        type="number" step="0.01" placeholder="Auto-calculated"
                        value={features.income_to_umr_ratio}
                        onChange={(e) => setFeatures((p) => ({ ...p, income_to_umr_ratio: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#f8fafc" }}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Credit Limit Utilization
                      <input
                        type="number" step="0.0001" placeholder="Auto-calculated"
                        value={features.credit_limit_utilization_ratio}
                        onChange={(e) => setFeatures((p) => ({ ...p, credit_limit_utilization_ratio: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#f8fafc" }}
                      />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Monthly Installment (IDR) {CRITICAL_BY_TAB[activeTab].includes("monthly_installment_estimate_idr") && <span style={{color:"#dc2626"}}>*</span>}
                      <input
                        type="number" placeholder="e.g. 650,000"
                        value={features.monthly_installment_estimate_idr}
                        onChange={(e) => {
                          const inst = toNumericInput(e.target.value);
                          setFeatures((p) => ({
                            ...p,
                            monthly_installment_estimate_idr: inst,
                            disposable_income_after_debt_idr: typeof p.monthly_income_idr === "number" && typeof inst === "number" ? p.monthly_income_idr - inst : p.disposable_income_after_debt_idr,
                            debt_service_ratio: typeof p.monthly_income_idr === "number" && typeof inst === "number" && p.monthly_income_idr > 0 ? Number((inst / p.monthly_income_idr).toFixed(3)) : p.debt_service_ratio,
                          }));
                        }}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Debt Service Ratio
                      <input
                        type="number" step="0.01" placeholder="Auto-calculated"
                        value={features.debt_service_ratio}
                        onChange={(e) => setFeatures((p) => ({ ...p, debt_service_ratio: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#f8fafc" }}
                      />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Debt-to-Income Ratio (DTI)
                      <input
                        type="number" step="0.01" placeholder="Auto-calculated"
                        value={features.debt_to_income_ratio}
                        onChange={(e) => setFeatures((p) => ({ ...p, debt_to_income_ratio: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#f8fafc" }}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
                      Financial Distress Index
                      <input
                        type="number" step="0.01" min={0} max={10} placeholder="e.g. 4.5 (optional)"
                        value={features.financial_distress_index}
                        onChange={(e) => setFeatures((p) => ({ ...p, financial_distress_index: toNumericInput(e.target.value) }))}
                        style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                      />
                    </label>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div style={{ padding: "10px 14px", borderRadius: "6px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", fontSize: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: "100%" }}>
                <Play size={14} />
                <span>{loading ? "Running Neural Inference…" : "Execute Prediction"}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Output Panel */}
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
                      {(Number(twp90Result.default_probability) * 100).toFixed(1)}%
                    </div>
                    <span className={`badge ${twp90Result.default_probability > 0.5 ? "badge-critical" : "badge-low"}`}>
                      {twp90Result.default_probability > 0.5 ? "HIGH TWP90 RISK" : "NORMAL REPAYMENT PROFILE"}
                    </span>
                  </div>

                  {twp90Result.defaulted_fields && twp90Result.defaulted_fields.length > 0 && (
                    <div style={{ padding: "8px 12px", background: "#fef3c7", border: "1px solid #fde68a", borderRadius: "6px", color: "#92400e", fontSize: "11px" }}>
                      <strong>Note:</strong> Score used default values for {twp90Result.defaulted_fields.length} missing field(s).
                    </div>
                  )}

                  <div className="stat-item-row">
                    <span className="stat-item-label">Serving Model Version</span>
                    <span className="stat-item-value">{twp90Result.model_version ?? "1"}</span>
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
                    Enter a Borrower Reference ID to load data from PostgreSQL or fill parameters to run scoring.
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
                        {Number(dtiResult.dti).toFixed(2)}x
                      </div>
                      <span className="badge badge-medium">Target Continuous</span>
                    </div>

                    <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
                      <span style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                        Financial Distress Index
                      </span>
                      <div style={{ fontSize: "28px", fontWeight: 800, color: dtiResult.financial_distress_index > 5 ? "#dc2626" : "#2563eb", margin: "6px 0" }}>
                        {Number(dtiResult.financial_distress_index).toFixed(2)}
                      </div>
                      <span className="badge badge-neutral">Range 0.0 - 10.0</span>
                    </div>
                  </div>

                  {dtiResult.defaulted_fields && dtiResult.defaulted_fields.length > 0 && (
                    <div style={{ padding: "8px 12px", background: "#fef3c7", border: "1px solid #fde68a", borderRadius: "6px", color: "#92400e", fontSize: "11px" }}>
                      <strong>Note:</strong> Score used default values for {dtiResult.defaulted_fields.length} missing field(s).
                    </div>
                  )}

                  <div className="stat-item-row">
                    <span className="stat-item-label">Serving Model Version</span>
                    <span className="stat-item-value">{dtiResult.model_version ?? "1"}</span>
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

                  {rootCauseResult.defaulted_fields && rootCauseResult.defaulted_fields.length > 0 && (
                    <div style={{ padding: "8px 12px", background: "#fef3c7", border: "1px solid #fde68a", borderRadius: "6px", color: "#92400e", fontSize: "11px" }}>
                      <strong>Note:</strong> Score used default values for {rootCauseResult.defaulted_fields.length} missing field(s).
                    </div>
                  )}

                  <div className="stat-item-row">
                    <span className="stat-item-label">Classifier Engine</span>
                    <span className="stat-item-value">LLM Rationale / Decision Tree Ensemble</span>
                  </div>
                  <div className="stat-item-row">
                    <span className="stat-item-label">Model Version</span>
                    <span className="stat-item-value">{rootCauseResult.model_version ?? "1"}</span>
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