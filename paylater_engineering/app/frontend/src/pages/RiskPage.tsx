import { useState } from "react";
import type { FormEvent } from "react";
import { AlertTriangle, Search } from "lucide-react";
import { assessTwp90 } from "../services/risk-service";
import { PageHeader } from "../components/ui/PageHeader";

export function RiskPage() {
  const [borrowerId, setBorrowerId] = useState("");
  const [features, setFeatures] = useState({ age: "", monthly_income_idr: "", regional_minimum_wage_umr_idr: "", num_active_lending_apps: "" });
  const [result, setResult] = useState<{ default_probability: number; model_version?: string | null } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResult(null); setLoading(true);
    try {
      const parsed = Object.fromEntries(Object.entries(features).map(([key, value]) => [key, Number(value)]));
      setResult(await assessTwp90({ borrower_id: borrowerId, features: parsed }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Assessment failed"); } finally { setLoading(false); }
  }
  return <><PageHeader eyebrow="Decision support" title="Risk intelligence" description="Run an authenticated TWP90 assessment using the production serving boundary." /><div className="risk-layout"><form className="panel form-panel" onSubmit={submit}><div className="panel-heading"><div><span className="eyebrow">TWP90 assessment</span><h3>Borrower inputs</h3></div><AlertTriangle size={19} className="text-amber" /></div><label>Borrower ID<input required value={borrowerId} onChange={(event) => setBorrowerId(event.target.value)} placeholder="ID_DEB_…" /></label>{Object.entries(features).map(([key, value]) => <label key={key}>{key.replaceAll("_", " ")}<input required type="number" value={value} onChange={(event) => setFeatures({ ...features, [key]: event.target.value })} /></label>)}<button className="primary-button" disabled={loading}><Search size={16} />{loading ? "Assessing…" : "Run assessment"}</button>{error && <div className="form-error">{error}</div>}</form><section className="panel result-panel"><span className="eyebrow">Verified model output</span><h3>Assessment result</h3>{result ? <div className="result-value"><strong>{(result.default_probability * 100).toFixed(1)}%</strong><span>Default probability</span><small>Model version: {result.model_version ?? "reported by backend"}</small></div> : <p className="panel-copy">Submit a borrower assessment to display the model response. Predictions are never generated in the browser.</p>}</section></div></>;
}
