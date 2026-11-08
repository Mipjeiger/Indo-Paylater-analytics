-- PayLater Indodana Database Schema
-- Idempotent migrations for paylater schema

CREATE SCHEMA IF NOT EXISTS paylater;

-- Main source table: paylater.database
CREATE TABLE IF NOT EXISTS paylater.database (
    borrower_id VARCHAR(50) PRIMARY KEY,
    age INTEGER,
    gender VARCHAR(20),
    province VARCHAR(100),
    education_level VARCHAR(100),
    employment_status VARCHAR(100),
    monthly_income_idr NUMERIC(18,2),
    regional_minimum_wage_umr_idr NUMERIC(18,2),
    num_active_lending_apps INTEGER,
    total_loan_outstanding_idr NUMERIC(18,2),
    credit_limit_granted_idr NUMERIC(18,2),
    loan_tenor_months INTEGER,
    daily_interest_rate_pct NUMERIC(8,4),
    primary_loan_purpose VARCHAR(200),
    debt_to_income_ratio NUMERIC(8,4),
    income_to_umr_ratio NUMERIC(8,4),
    credit_limit_utilization_ratio NUMERIC(8,4),
    monthly_installment_estimate_idr NUMERIC(18,2),
    debt_service_ratio NUMERIC(8,4),
    disposable_income_after_debt_idr NUMERIC(18,2),
    days_past_due INTEGER,
    financial_distress_index NUMERIC(8,4),
    twp90_default_status VARCHAR(100),
    primary_default_root_cause VARCHAR(200),
    cot_financial_psychology_rationale TEXT,
    confidence_score NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model versions registry
CREATE TABLE IF NOT EXISTS paylater.model_versions (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    version VARCHAR(100) NOT NULL,
    stage VARCHAR(50) DEFAULT 'candidate',
    algorithm VARCHAR(100),
    mlflow_run_id VARCHAR(100),
    artifact_path TEXT,
    feature_columns JSONB,
    metrics JSONB,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_at TIMESTAMP,
    promoted_by VARCHAR(100),
    is_active BOOLEAN DEFAULT FALSE,
    UNIQUE(task_name, version)
);

-- Predictions log (Inline indexes removed)
CREATE TABLE IF NOT EXISTS paylater.predictions (
    id SERIAL PRIMARY KEY,
    borrower_id VARCHAR(50) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(100),
    prediction JSONB NOT NULL,
    prediction_score NUMERIC(8,6),
    features JSONB,
    inference_latency_ms NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Actions log (Inline indexes removed)
CREATE TABLE IF NOT EXISTS paylater.actions_log (
    id SERIAL PRIMARY KEY,
    borrower_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    action_status VARCHAR(50) NOT NULL,
    rule_code VARCHAR(100),
    recommendation TEXT,
    metadata JSONB,
    executed_by VARCHAR(100) DEFAULT 'system',
    idempotency_key VARCHAR(200) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drift reports (Inline indexes removed)
CREATE TABLE IF NOT EXISTS paylater.drift_reports (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    drift_type VARCHAR(100) NOT NULL,
    drift_score NUMERIC(8,6),
    drift_detected BOOLEAN DEFAULT FALSE,
    reference_window VARCHAR(100),
    comparison_window VARCHAR(100),
    feature_drift JSONB,
    report_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for data table
CREATE INDEX IF NOT EXISTS idx_data_borrower ON paylater.data (borrower_id);
CREATE INDEX IF NOT EXISTS idx_data_twp90 ON paylater.data (twp90_default_status);
CREATE INDEX IF NOT EXISTS idx_data_root_cause ON paylater.data (primary_default_root_cause);

-- Indexes for predictions table
CREATE INDEX IF NOT EXISTS idx_predictions_borrower ON paylater.predictions (borrower_id);
CREATE INDEX IF NOT EXISTS idx_predictions_task ON paylater.predictions (task_name);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON paylater.predictions (created_at);

-- Indexes for actions_log table
CREATE INDEX IF NOT EXISTS idx_actions_borrower ON paylater.actions_log (borrower_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON paylater.actions_log (action_status);

-- Indexes for drift_reports table
CREATE INDEX IF NOT EXISTS idx_drift_task ON paylater.drift_reports (task_name);
CREATE INDEX IF NOT EXISTS idx_drift_created ON paylater.drift_reports (created_at);