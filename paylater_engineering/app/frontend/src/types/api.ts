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
};

export type DashboardKpis = {
  total_borrowers: number;
  active_borrowers: number;
  outstanding_exposure: number;
  repayment_rate: number;
  twp90_rate: number;
};
