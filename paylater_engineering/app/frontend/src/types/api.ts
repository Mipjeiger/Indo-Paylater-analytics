export type ApiError = {
  status: number;
  message: string;
};

export type HealthResponse = { status: string };

export type Twp90Request = {
  borrower_id: string;
  features: Record<string, unknown>;
};

export type Twp90Response = {
  borrower_id: string;
  default_probability: number;
  model_version?: string | null;
};

export type DtiResponse = {
  borrower_id: string;
  dti: number;
  financial_distress_index: number;
  model_version?: string | null;
};

export type RootCauseResponse = {
  borrower_id: string;
  root_cause: string;
  model_version?: string | null;
  confidence?: number;
  defaulted_fields?: string[];
};

export type DashboardKpis = {
  total_borrowers: number;
  active_borrowers: number;
  outstanding_exposure: number;
  repayment_rate: number;
  twp90_rate: number;
  average_dti?: number;
  high_risk_count?: number;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type BorrowerRecord = {
  borrower_id: string;
  age: number | null;
  gender: string | null;
  province: string | null;
  education_level: string | null;
  employment_status: string | null;
  monthly_income_idr: number | null;
  total_loan_outstanding_idr: number | null;
  credit_limit_granted_idr?: number | null;
  credit_limit_utilization_ratio?: number | null;
  debt_to_income_ratio: number | null;
  days_past_due?: number | null;
  financial_distress_index?: number | null;
  risk_score: number | null;
  risk_short: string | null;
  is_high_risk: boolean | null;
  twp90_default_status: string | null;
  primary_default_root_cause: string | null;
  primary_loan_purpose?: string | null;
  updated_at: string | null;
};

export type DecisionRecord = {
  id: number;
  borrower_id: string;
  action_type: string;
  action_status: string;
  rule_code: string | null;
  recommendation: string | null;
  executed_by: string;
  idempotency_key: string | null;
  created_at: string;
};

export type PortfolioSummary = {
  total_borrowers: number;
  outstanding_exposure: number;
  average_dti: number;
  high_risk_borrowers: number;
  defaulted_borrowers: number;
  average_utilization_rate?: number;
  average_recovery_rate?: number;
};

export type BorrowerPortfolioRecord = {
  borrower_id: string;
  age: number | null;
  gender: string | null;
  province: string | null;
  education_level: string | null;
  employment_status: string | null;
  monthly_income_idr: number | null;
  regional_minimum_wage_umr_idr?: number | null;
  num_active_lending_apps?: number | null;
  total_loan_outstanding_idr: number | null;
  credit_limit_granted_idr: number | null;
  loan_tenor_months?: number | null;
  daily_interest_rate_pct?: number | null;
  credit_limit_utilization_ratio: number | null;
  debt_to_income_ratio: number | null;
  income_to_umr_ratio?: number | null;
  monthly_installment_estimate_idr?: number | null;
  debt_service_ratio?: number | null;
  disposable_income_after_debt_idr?: number | null;
  days_past_due: number | null;
  financial_distress_index: number | null;
  risk_score: number | null;
  risk_short: string | null;
  is_high_risk: boolean | null;
  twp90_default_status: string | null;
  primary_default_root_cause: string | null;
  primary_loan_purpose: string | null;
  updated_at: string | null;
  recent_actions: DecisionRecord[];
  recent_predictions: Record<string, unknown>[];
};

export type ModelVersionRecord = {
  id: number;
  task_name: string;
  model_name: string;
  version: string;
  stage: string;
  algorithm: string | null;
  mlflow_run_id: string | null;
  artifact_path: string | null;
  feature_columns: string[] | null;
  metrics: Record<string, unknown> | null;
  trained_at: string;
  promoted_at: string | null;
  promoted_by: string | null;
  is_active: boolean;
};

export type AuditEvent = {
  event_type: "action" | "prediction" | "drift";
  occurred_at: string;
  borrower_id: string | null;
  status: string;
  details: Record<string, unknown>;
};
