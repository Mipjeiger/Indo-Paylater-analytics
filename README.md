# 💳 PayLater Indodana Engineering

## 🚀 Production-oriented ML and MLOps platform

PayLater Indodana Engineering is a Python-based machine-learning platform for
pay-later portfolio risk intelligence. The repository combines:

- borrower and loan data storage;
- leakage-aware feature definitions;
- supervised model training flows;
- model serving through FastAPI;
- model and artifact tracking through MLflow and MinIO;
- online/offline feature-store infrastructure through Feast, PostgreSQL, and
  Redis;
- deterministic action and notification services;
- Prometheus metrics and statistical drift reporting; and
- a React/TypeScript business-facing frontend.

The engineering objective is to separate the lifecycle of data, features,
training, model artifacts, inference, monitoring, and business actions. A
prediction should be reproducible from its model version, input features, and
request context rather than being an opaque value produced inside an API
handler.

> **Current implementation status:** this repository contains an active
> engineering foundation and several working integration surfaces. Some
> enterprise endpoints and operational hardening remain outstanding. The
> limitations section below is part of the operating documentation and should
> be reviewed before production deployment.

## 🧰 Technology stack

The following stack is defined by `docker-compose.yml`, the Python dependency
manifest, and the frontend package manifest:

### 🌐 Application and API

- **Python 3.11** — runtime used by the API and Prefect containers.
- **FastAPI** — HTTP API framework.
- **Uvicorn** — ASGI server for FastAPI.
- **Pydantic** — request and configuration validation.
- **React and TypeScript** — frontend application.
- **Vite** — frontend development server and production bundler.
- **React Router** — frontend navigation.
- **TanStack Query** — frontend server-state and request lifecycle management.
- **Lucide React** — frontend interface icons.

### 🗄️ Data and persistence

- **PostgreSQL 16** — relational source data, model registry metadata,
  predictions, action logs, and drift reports.
- **SQLAlchemy** — Python database engine and registry integration.
- **psycopg2-binary** — PostgreSQL driver.
- **Redis 7** — cache and Feast online-store backend.
- **RedisInsight** — local Redis inspection interface.
- **Apache Parquet and Pandas** — source dataset and tabular data processing.

### 🤖 Machine learning and feature engineering

- **CatBoost** — TWP90 binary classification.
- **LightGBM** — root-cause multiclass classification.
- **TensorFlow/Keras** — DTI and financial-distress multi-output regression.
- **scikit-learn** — preprocessing, splitting, and evaluation utilities.
- **SHAP** — model explanation support for root-cause modeling.
- **Feast** — feature-store definitions and online/offline feature retrieval.

### 📦 MLOps and artifact management

- **MLflow** — experiment tracking, model metadata, and artifact management.
- **MinIO** — S3-compatible object storage for model artifacts.
- **Prefect** — training workflow orchestration.
- **python-dotenv** — environment configuration loading.

### 📈 Monitoring and platform operations

- **Prometheus** — pull-based metrics collection.
- **Grafana** — metrics dashboards and visualization.
- **Docker** — application containerization.
- **Docker Compose** — local multi-service orchestration.

## 🎯 Business and ML scope

### Dataset contract

The source file is
[`paylater_engineering/database/dataset/indonesia_fintech_paylater.parquet`](paylater_engineering/database/dataset/indonesia_fintech_paylater.parquet).
Inspection of that file found 10,000 rows, 30 columns, no null values, and
10,000 distinct `borrower_id` values. It has no source timestamp column.
`borrower_id` is the entity identifier and is the primary key in the
PostgreSQL migration.

The exact Parquet columns are grouped below by their current business use:

- **Identifier:** `borrower_id`.
- **Borrower profile:** `age`, `gender`, `province`, `education_level`,
  `employment_status`.
- **Income and lending:** `monthly_income_idr`,
  `regional_minimum_wage_umr_idr`, `num_active_lending_apps`,
  `total_loan_outstanding_idr`, `credit_limit_granted_idr`,
  `loan_tenor_months`, `daily_interest_rate_pct`, `primary_loan_purpose`.
- **Ratios and repayment measures:** `debt_to_income_ratio`,
  `income_to_umr_ratio`, `credit_limit_utilization_ratio`,
  `monthly_installment_estimate_idr`, `debt_service_ratio`,
  `disposable_income_after_debt_idr`, `financial_distress_index`.
- **Delinquency and labels:** `days_past_due`, `twp90_default_status`,
  `primary_default_root_cause`.
- **Derived risk and explanation fields:** `cot_financial_psychology_rationale`,
  `confidence_score`, `risk_score`, `risk_short`, `is_high_risk`,
  `distress_bin`.

The inspected Pandas dtypes are: `int64` for `age`,
`monthly_income_idr`, `regional_minimum_wage_umr_idr`,
`num_active_lending_apps`, `total_loan_outstanding_idr`,
`credit_limit_granted_idr`, `loan_tenor_months`, and `days_past_due`;
`int8` for `risk_score`; `float64` for `daily_interest_rate_pct`,
`debt_to_income_ratio`, `income_to_umr_ratio`,
`credit_limit_utilization_ratio`, `monthly_installment_estimate_idr`,
`debt_service_ratio`, `disposable_income_after_debt_idr`,
`financial_distress_index`, and `confidence_score`; `category` for
`twp90_default_status` and `risk_short`; `bool` for `is_high_risk`; and
`object` for the remaining nine text columns.

The observed `twp90_default_status` values are `Current-Performing`,
`Default-Macet-TWP90`, `Doubtful-DPD61-90`, `Special-Mention-DPD1-30`, and
`Substandard-DPD31-60`.

### Data and feature flow

The ETL reads the Parquet file and appends its rows in batches to
`paylater.database` in PostgreSQL. The training flows read from PostgreSQL;
the Parquet file is not the common runtime training source for all three tasks.
The ETL uses append behavior rather than upsert, so rerunning it against an
already populated table is not an idempotent refresh.

Feast reads the PostgreSQL source and defines five borrower feature views:
`borrower_profile`, `loan_behavior`, `dti_inputs`, `engineered_ratios`, and
`twp90_signals`. Redis is the configured online store, with a one-hour key
TTL. Feast's native Redis representation is serialized and is not intended
for direct human-readable inspection. The separate readable-hash projection
uses the `MIRROR_KEY_PREFIX` application setting; the Feast Compose service
must receive that setting for the projection to use the intended key prefix.
The projection is for inspection and is not Feast's online representation.

### Implemented model tasks

| Task | Training implementation | Target / API result | Current split and evaluation |
|---|---|---|---|
| TWP90 | CatBoost binary classifier | The training label is `0` only for `Current-Performing`; every other `twp90_default_status` value is mapped to `1`. The API returns `default_probability`. | 70% / 15% / 15%, sorted by the PostgreSQL `created_at` field; reports PR-AUC, recall at 95% precision, accuracy, and a validation-to-test PR-AUC gap. |
| DTI and distress | TensorFlow/Keras multi-output regression | `debt_to_income_ratio` and `financial_distress_index`; the scoring API returns `dti` and `financial_distress_index`. | 80% / 20% after sorting by `borrower_id`; reports MSE, R², MAE, and MAPE overall and per target. |
| Root cause | LightGBM, Random Forest, and Decision Tree candidates | `primary_default_root_cause`, with five labels: `Compulsive-FOMO-Spending`, `Gali-Lubang-Debt-Spiral`, `High-Interest-Rate-Compounding`, `Income-Shock-Underemployment`, and `Speculative-Losses`. The API returns `root_cause` and `confidence`. | 80% / 20%; reports balanced accuracy and quadratic weighted kappa. The flow ranks candidates by QWK but currently registers the LightGBM model for serving. |

The training feature preparation excludes each task's target and configured
leakage fields. These are implementation-level controls, not evidence that
the current dataset represents a production-time snapshot.

### Model and API integration

The three training flows track runs and register model versions in MLflow.
Model artifacts are also uploaded to the configured MinIO bucket; the DTI
flow stores its scaler there alongside the model. The API serving modules
resolve a Production version first, then Staging, then the newest available
version. The scoring/classification routes are `/score/twp90`,
`/score/dti-distress/{borrower_id}`, and
`/classify/root-cause/{borrower_id}`. The two `/score` routes persist
successful predictions to `paylater.predictions`; the root-cause route
currently does not use that prediction logger.

### Data and evaluation limits

PostgreSQL adds `created_at` and `updated_at` columns that are not in the
Parquet source. The TWP90 flow orders rows by database `created_at`, but that
field is not an authoritative borrower observation or event timestamp.
Consequently, its current 70/15/15 split should not be described as a valid
historical temporal evaluation. The DTI and root-cause splits are row-based,
not time-based; the PostgreSQL root-cause load also has no explicit
`ORDER BY`. In addition, the TWP90 target mapping treats every status other
than `Current-Performing` as positive, including statuses besides
`Default-Macet-TWP90`.
Confirm that mapping against the intended business definition before
interpreting its output as a 90-day-default probability. A production
temporal evaluation requires a reliable observation timestamp and a
business-approved target definition.

## 🏗️ Architecture

```text
Phase 1.
CLIENT REQUEST AND INFERENCE

[Browser]
    |
    | HTTP
    v
[React SPA + Nginx :8085] -- proxy /api, /score, /classify, /health -->
                                  [FastAPI :8000; API + model serving]
                                          |
              +---------------------------+--------------------------+
              |                           |                          |
              v                           v                          v
   log TWP90/DTI predictions   resolve/load model version    load DTI scaler
              |                           |                          |
              v                           v                          v
   [PostgreSQL :5432]          [MLflow :5000]               [MinIO :9000]

Phase 2.
MODEL TRAINING AND REGISTRATION

[Explicit flow invocation in FastAPI container]
                    |
                    v
[Prefect flow: app/training/flows] -- reports run state --> [Prefect server :4200]
                    |
                    | reads training data
                    v
             [PostgreSQL :5432]
                    |
                    | rows used by the training tasks
                    v
       [Train and evaluate model]
                    |
          +---------+----------+
          |                    |
          | log run/register   | upload model/scaler artifacts
          v                    v
    [MLflow :5000] -- artifact store --> [MinIO :9000]
          |
          | tracking metadata
          v
    [PostgreSQL :5432]

Phase 3.
OFFLINE AND ONLINE FEATURES

[PostgreSQL :5432] -- offline source --> [Feast :6566]
                                              |
                                              | materialize online features
                                              | and refresh readable projection
                                              v
                                      [Redis DB 0 :6379]
                                              ^
                                              | inspect
                                      [RedisInsight :8081]

Phase 4.
MONITORING

[FastAPI :8000] -- exposes /metrics --> [Prometheus :9090]
                                               ^
                                               | queries metrics
                                        [Grafana :3000]
```

In Compose, model serving is part of the FastAPI container, not a separate
service. Training flows read PostgreSQL and connect to MLflow and MinIO; they
do not receive training data from Feast. Feast independently reads the
PostgreSQL offline source and materializes to Redis. The current scoring routes
accept feature values in their API requests and load registered models through
MLflow; they do not currently use Feast retrieval for request features.

The Prefect server provides the orchestration API. Compose does not define a
Prefect worker or scheduled deployment for these training flows, so starting
the server alone does not start model training. The frontend image serves the
React build with Nginx, which proxies API and scoring paths to FastAPI.
Prometheus scrapes FastAPI's metrics endpoint, and Grafana queries Prometheus.

### 🔌 Service responsibilities

| Service | Compose port | Responsibility |
|---|---:|---|
| PostgreSQL | `5432` | PayLater source and operational tables; MLflow tracking backend |
| Redis | `6379` | Feast online-store backend and readable inspection projection (configure `MIRROR_KEY_PREFIX`) |
| RedisInsight | `8081` | Local Redis inspection UI |
| Feast | `6566` (`8888` mapped for optional UI) | Feature registry, online serving, materialization, and readable projection refresh |
| MinIO API | `9000` | S3-compatible model/artifact storage |
| MinIO Console | `9001` | Local object-storage UI |
| FastAPI | `8000` | HTTP API, model inference, prediction logging, and `/metrics` |
| MLflow | `5002` (container `5000`) | Experiment tracking and model registry |
| Prefect | `4200` | Workflow orchestration API; no worker/deployment is defined in Compose |
| Prometheus | `9090` | Pull-based metrics collection from FastAPI |
| Grafana | `3000` | Metrics visualization using Prometheus |
| Frontend | `8085` (`5173` for local Vite development) | React SPA served by Nginx; proxies API requests to FastAPI |

All Compose services use the `paylater_indodana` bridge network. Persistent
state is stored in named volumes: `pgdata`, `redis_data`,
`redisinsight_data`, `minio_data`, `mlflow_data`, `prefect_data`,
`prometheus_data`, and `grafana_data`.

## 🗂️ Repository layout

```text
paylater_engineering/
├── app/
│   ├── actions/              # Rules, action audit logging, notifications
│   ├── api/                  # FastAPI application and routers
│   ├── feast/                # Entities, sources, feature views, retrieval
│   ├── frontend/             # React/TypeScript/Vite business frontend
│   ├── monitoring/           # Prometheus metrics and drift calculations
│   ├── registry/             # SQLAlchemy connection and model metadata APIs
│   ├── serving/              # Cached MLflow model loading and inference
│   └── training/flows/       # Prefect model-training flows
├── database/
│   ├── dataset/              # Parquet source dataset
│   ├── etl/                  # Parquet-to-PostgreSQL loader
│   ├── migrations/           # PostgreSQL schema migration
│   └── tests/                # Database tests
├── docker/
│   ├── api.Dockerfile
│   ├── feast.Dockerfile
│   ├── prefect.Dockerfile
│   └── requirements.txt
├── prometheus/prometheus.yml
├── docker-compose.yml
└── .env.example
```

## ✅ Prerequisites

Install the following locally:

- Docker Desktop or Docker Engine with Docker Compose;
- Git;
- Node.js and npm for the frontend; and
- Python 3.11 for local scripts and tests.

The main runtime dependencies are installed in the FastAPI image from
`docker/requirements.txt`. The frontend dependencies are declared in
`app/frontend/package.json`.

## ⚙️ Configuration

Configure runtime settings through the deployment environment or an external
secret manager. Do not copy credentials, passwords, API keys, or local secret
files into this README.

The Compose stack consumes configuration names including
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_SCHEMA`, `MINIO_ENDPOINT`, `MINIO_ROOT_USER`,
`MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`, `MLFLOW_TRACKING_URI`,
`PREFECT_API_URL`, `REDIS_URL`, `ACTION_KILL_SWITCH`, and `AUTO_BLOCK`.
Provide their values through the runtime environment used to launch Compose.

The Compose file passes service-to-service hostnames such as `postgres`,
`redis`, `minio`, `mlflow`, and `prefect`. From the host machine, use
`localhost` and the published port instead.

The FastAPI application allows the local Vite origins configured through
`FRONTEND_ORIGINS`. Update that variable for any non-local deployment.

## 🛠️ Step-by-step local startup and engineering workflow

The recommended order is **preflight → tests → infrastructure → schema and
data → MLflow/Prefect → training → API → monitoring → frontend**. Do not start
model-serving smoke tests before a compatible model has been registered.

### 0. 🧭 Preflight

Run all commands from the repository directory:

```bash
cd /path/to/paylater_fintech/paylater_engineering
```

Confirm the required tools:

```bash
docker --version
docker compose version
python3 --version
node --version
npm --version
```

Provide runtime configuration through the deployment environment before
starting Compose. Required service configuration includes PostgreSQL, MinIO,
Redis, MLflow, Prefect, and Grafana settings. Do not place real credentials in
the repository or in this README.

### 1. 🧪 Run local Python and frontend checks

Run syntax checks before starting services:

```bash
python3 -m compileall -q app database
```

Run the Python tests:

```bash
PYTHONPATH=. pytest -q
```

PostgreSQL integration tests require a test DSN:

```bash
export PAYLATER_TEST_POSTGRES_DSN='postgresql://<user>:<password>@localhost:5432/<test_database>'
PYTHONPATH=. pytest -q database/tests app/registry/tests
```

Install and build the frontend independently:

```bash
cd app/frontend
npm install
npm run build
cd ../..
```

Do not treat a successful frontend build as proof that the backend is healthy;
the build checks TypeScript and bundling only.

### 2. 🐳 Start stateful infrastructure

Start the services required by PostgreSQL, ETL, Feast, training artifacts, and
the API:

```bash
docker compose up -d postgres redis minio
docker compose ps
```

Wait until PostgreSQL, Redis, and MinIO report healthy status:

```bash
docker compose ps --format "table {{.Name}}\t{{.Service}}\t{{.State}}\t{{.Health}}"
```

Useful service checks:

```bash
curl http://localhost:9000/minio/health/ready
redis-cli -h localhost ping
```

PostgreSQL is exposed on `localhost:5432`, Redis on `localhost:6379`, and
MinIO exposes its API on `localhost:9000` and console on `localhost:9001`.

### 3. 🗃️ Initialize and verify the database

The PostgreSQL container mounts `database/migrations` into its initialization
directory. Initialization scripts run automatically only when the PostgreSQL
data volume is first created.

Inspect database logs:

```bash
docker compose logs postgres
```

For a clean disposable development database only, remove the named volume
before restarting:

```bash
docker compose down
docker volume rm paylater_engineering_pgdata
docker compose up -d postgres
```

Do not remove the volume in an environment containing data that must be
preserved.

The migration creates `paylater.database` and initializes the schema used by
the ETL and Feast PostgreSQL source. Verify the migration has completed before
loading data.

### 4. 📥 Load the Parquet dataset

The source file is:

```text
database/dataset/indonesia_fintech_paylater.parquet
```

Run the ETL from the project root so both `app` and `database` resolve:

```bash
PYTHONPATH=. python3 -m database.etl.etl_data_to_postgres
```

The ETL requires PostgreSQL connectivity and the configured dataset path. Check
the ETL output and database row counts before training. Do not rerun an ETL
against a shared environment without confirming its append/upsert behavior.

### 5. 🧩 Start Feast and readable Redis projection

The single Feast container applies the definitions in `app/feast`, starts the
Feast server, and supervises the readable-projection refresh loop. It
materializes the complete current PostgreSQL source and writes every borrower's
online features to readable Redis hashes in bounded batches.

Run this after the ETL has loaded `paylater.database`:

```bash
docker compose up -d --build postgres redis feast
docker compose ps postgres redis feast
docker compose logs --tail=100 feast
```

The refresh loop updates the projection every 40 minutes. Both Feast's native
online keys and readable hashes use a one-hour TTL. The Redis configuration
rewrites unchanged source rows during each full refresh so their TTLs renew.
PostgreSQL remains the source of truth; Redis can be rebuilt from it.

Feast's native keys use a binary encoding and may look like replacement
symbols in RedisInsight. Do not edit or rename them. The readable projection
uses separate keys in the same Redis database (DB 0), so it does not interfere
with Feast retrieval:

```text
paylater_indodana:borrower:<borrower_id>
```

Verify that all borrower hashes are present and have a live TTL:

```bash
docker compose exec redis sh -c \
  'redis-cli --scan --pattern "paylater_indodana:borrower:*" | wc -l'
docker compose exec redis sh -c \
  'key=$(redis-cli --scan --pattern "paylater_indodana:borrower:*" | head -n 1); redis-cli TTL "$key"'
docker compose exec redis redis-cli HGETALL \
  paylater_indodana:borrower:ID_DEB_00264B68D1
```

The first command should match the row count in `paylater.database`; the TTL
should be positive and no greater than 3600 seconds. In RedisInsight, connect
to host `redis`, port `6379`, and database index `0`, then search for
`paylater_indodana:borrower:*`. The readable hash fields are feature-view
qualified, for example `borrower_profile__gender`.

If Feast exits or no hashes appear, inspect its logs and confirm
that PostgreSQL contains borrower rows:

```bash
docker compose logs --tail=200 feast
docker compose exec postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM paylater.database"'
```

The projection contains a readable duplicate of borrower feature data and is
for local development/inspection, not production Redis. Because Feast serving
and refresh share one container, stopping the projection also stops Feast:
`docker compose stop feast`.

Do not expose Feast directly to the browser. The API and model-serving
components remain the controlled boundary for feature retrieval.

### 6. 🔬 Start MLflow and Prefect

```bash
docker compose up -d mlflow prefect
docker compose ps mlflow prefect
docker compose logs --tail=100 mlflow prefect
```

Verify the UIs:

- MLflow: <http://localhost:5000>
- Prefect: <http://localhost:4200>

MLflow stores tracking metadata in PostgreSQL and artifacts in the MinIO
`paylater-models` location configured by Compose. Prefect provides the
orchestration server; the training flows still need to be submitted or
executed with a configured Prefect API URL.

### 7. 🧠 Execute model training

The training flows are:

```text
Task 1: Training TWP90 flows
docker compose exec -e PREFECT_API_URL=http://prefect:4200/api fastapi python -c "from app.training.flows.task1_twp90 import task1_flow; print(task1_flow())"

Task 2: DTI Distress Training Flow
docker compose exec -e PREFECT_API_URL=http://prefect:4200/api fastapi python -c \
"from app.training.flows.task2_dti_distress import task2_flow; print(task2_flow('/workspace/database/dataset/indonesia_fintech_paylater.parquet'))"

Task 3: Root Cause Analysis Training Flow
docker compose exec -e PREFECT_API_URL=http://prefect:4200/api fastapi python -c \
"from app.training.flows.task3_root_cause import task3_flow; print(task3_flow('/workspace/database/dataset/indonesia_fintech_paylater.parquet'))"
```

Before training, confirm:

1. the Parquet dataset is readable;
2. PostgreSQL and MinIO are healthy;
3. MLflow is reachable;
4. MinIO endpoint and runtime credentials are available;
5. the target columns exist; and
6. the feature leakage rules match the task.

The flows can be invoked from the project root with Prefect’s Python API:

```bash
PYTHONPATH=. python3 -c \
  'from app.training.flows.task1_twp90 import task1_flow; task1_flow()'

PYTHONPATH=. python3 -c \
  'from app.training.flows.task2_dti_distress import task2_flow; task2_flow()'

PYTHONPATH=. python3 -c \
  'from app.training.flows.task3_root_cause import task3_flow; task3_flow()'
```

Run one task at a time and inspect its output before starting the next task.
Training artifacts are uploaded to MinIO under task-specific keys:

```text
s3://paylater-models/models/twp90/<mlflow_run_id>/twp90.cbm
s3://paylater-models/models/dti_distress/<mlflow_run_id>/dti_distress.keras
s3://paylater-models/models/dti_distress/<mlflow_run_id>/dti_distress_scaler.npz
s3://paylater-models/models/root_cause/<mlflow_run_id>/root_cause.txt
```

The flows use temporary serialization files and do not intentionally retain a
local model directory. Confirm the MLflow run and MinIO object exist before
attempting inference. The current serving layer resolves registered MLflow
model versions, so uploading a raw object to MinIO alone is not sufficient;
the artifact must also be registered through the model-serving/registry
workflow.

### 8. ⚡ Build and start the FastAPI service

Rebuild when changing Python dependencies, Docker configuration, or copied
application files:

```bash
docker compose build fastapi
docker compose up -d fastapi
docker compose ps fastapi
docker compose logs --tail=100 fastapi
```

The API container uses `/workspace` and exposes the package as
`/workspace/app`. This avoids the import failure caused by mounting
`./app:/app`, which hides the expected `app` package layout.

Verify the registered routes:

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/metrics/
```

Current model routes:

```text
POST /score/twp90
GET  /score/dti-distress/{borrower_id}
POST /classify/root-cause/{borrower_id}
```

### 9. 🩺 Run API smoke tests

Health and metrics:

```bash
curl --fail http://localhost:8000/health/
curl --fail http://localhost:8000/metrics/
```

TWP90 request shape:

```bash
curl --fail -X POST http://localhost:8000/score/twp90 \
  -H "Content-Type: application/json" \
  -d '{
    "borrower_id": "ID_DEB_EXAMPLE",
    "features": {
      "age": 28,
      "monthly_income_idr": 8630000,
      "regional_minimum_wage_umr_idr": 2950000,
      "num_active_lending_apps": 1
    }
  }'
```

If model registration or artifacts are incomplete, a model endpoint should
return an explicit service/model error. Do not replace the error with a
fabricated prediction.

### 10. 📊 Start monitoring

```bash
docker compose up -d prometheus grafana
docker compose ps prometheus grafana
```

Open:

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>

Prometheus scrapes FastAPI through the Compose network at
`http://fastapi:8000/metrics/`. Check the Prometheus targets page and confirm
the `paylater-api` target is up before relying on dashboard values.

### 11. 🖥️ Start the frontend

Configure the frontend API base URL through the local frontend environment:

```bash
cd app/frontend
printf '%s\n' 'VITE_API_BASE_URL=http://localhost:8000' > .env.local
npm install
npm run dev
```

Open <http://localhost:5173>.

The frontend uses the registered FastAPI health, metrics, TWP90, DTI/distress,
and root-cause routes. Pages whose aggregation APIs are not registered display
an explicit unavailable state instead of fabricated borrower, portfolio,
model, or audit data.

### 12. 🛑 Stop services

Stop containers while preserving named volumes:

```bash
docker compose stop
```

Stop and remove containers and the Compose network:

```bash
docker compose down
```

Do not add `--volumes` unless you intentionally want to delete local
PostgreSQL, MinIO, MLflow, Prefect, Prometheus, and Grafana state.

## 🔗 API examples

TWP90 assessment:

```bash
curl -X POST http://localhost:8000/score/twp90 \
  -H "Content-Type: application/json" \
  -d '{
    "borrower_id": "ID_DEB_EXAMPLE",
    "features": {
      "age": 28,
      "monthly_income_idr": 8630000,
      "regional_minimum_wage_umr_idr": 2950000,
      "num_active_lending_apps": 1
    }
  }'
```

Health:

```bash
curl http://localhost:8000/health/
```

Prometheus metrics:

```bash
curl http://localhost:8000/metrics/
```

## 🧾 Database and model registry

The migration creates the `paylater` schema and these logical tables:

- `paylater.database`: source borrower and loan features;
- `paylater.model_versions`: model version metadata;
- `paylater.predictions`: inference records;
- `paylater.actions_log`: action audit records and idempotency keys; and
- `paylater.drift_reports`: persisted drift results.

The registry implementation in `app/registry/` provides SQLAlchemy connection
management, pooled engines, migration execution, model-version registration,
active-version lookup, and promotion operations.

JSONB is reserved for variable-shaped model metadata, predictions, features,
action metadata, and drift details. Stable source fields remain relational
columns so they can be indexed and constrained.

## 🧩 Feature store

`app/feast/` defines:

- `borrower` as the entity keyed by `borrower_id`;
- PostgreSQL-backed source data;
- Redis online-store configuration;
- borrower profile features;
- loan behavior features;
- DTI inputs;
- TWP90 signals; and
- engineered ratios.

Leakage-sensitive fields are excluded from model-facing feature definitions.
In particular, target and post-outcome fields are not treated as ordinary
model inputs. Feature retrieval is designed to occur through Feast rather than
direct browser access to PostgreSQL or Redis.

## 🛡️ Business actions and safety defaults

The action layer separates deterministic rule evaluation, action logging, and
optional notifications. The safe defaults are:

```dotenv
ACTION_KILL_SWITCH=0
AUTO_BLOCK=0
```

No automatic blocking should be enabled without verified authorization,
business policy, idempotency, and audit requirements. Slack notifications are
optional and require a configured webhook; the application should not depend
on Slack being present for core scoring.

### Monitoring and Slack automation

Drift and action metrics are exported through `/metrics/` and scraped by
Prometheus:

```text
paylater_drift_detected
paylater_action_outcomes_total
```

Grafana is provisioned with the Prometheus datasource and the
`PayLater Monitoring` dashboard. Open:

- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- Metrics: <http://localhost:8000/metrics/>

`DRIFT_STATUS` is populated by `persist_drift_report()` for each feature in a
drift report. `ACTION_OUTCOMES` is incremented by `block_borrower()` and Slack
delivery outcomes. The metrics module initializes zero-valued baseline label
sets so Grafana can query the metrics before the first real event.

To enable API-hit Slack delivery, set these runtime variables in the Compose
environment without writing values to source control:

```dotenv
SLACK_NOTIFY_ON_API_HIT=1
SLACK_WEBHOOK_URL=<incoming-webhook-url>
```

Restart FastAPI and Grafana after changing runtime configuration:

```bash
docker compose up -d --build fastapi grafana prometheus
docker compose restart fastapi grafana prometheus
docker compose ps fastapi grafana prometheus
```

The root-cause, TWP90, and DTI endpoints send notifications as FastAPI
background tasks after success or a handled `503` inference failure. Health
checks and Prometheus metric scrapes do not generate Slack messages.

Verify Slack delivery with the root-cause endpoint:

```bash
curl --fail -X POST http://localhost:8000/classify/root-cause/ID_DEB_0DE3583B12 \
  -H "Content-Type: application/json" \
  -d 'features: {...}'
```

Verify metrics directly:

```bash
curl --fail http://localhost:8000/metrics/ |
  grep -E 'paylater_(drift_detected|action_outcomes_total|http_requests_total)'
```

## 📡 Monitoring and observability

Prometheus metrics are defined centrally in `app/monitoring/metrics.py`.
The FastAPI metrics endpoint is scraped by Prometheus. Drift calculations in
`app/monitoring/drift.py` support:

- population stability index for numerical features;
- Kolmogorov-Smirnov comparison for numerical distributions;
- chi-square comparison for categorical distributions;
- missing-value filtering; and
- small-sample validation.

Drift reports can be persisted through `app/monitoring/exporter.py`.

## 🧪 Development checks

Python syntax checks:

```bash
cd paylater_engineering
python3 -m compileall -q app database
```

Backend tests:

```bash
cd paylater_engineering
PYTHONPATH=. pytest -q
```

Frontend build:

```bash
cd paylater_engineering/app/frontend
npm run build
```

PostgreSQL integration tests require a test database DSN:

```bash
export PAYLATER_TEST_POSTGRES_DSN='postgresql://user:password@localhost:5432/paylater_test'
PYTHONPATH=. pytest -q database/tests app/registry/tests
```

## 🔁 CI/CD automation

GitHub Actions provides automated quality gates, security checks, integration
checks, and build validation. CI uses disposable service containers and
workflow-scoped test values; it does not access production systems or
credentials.

### Continuous integration

Workflow: `.github/workflows/ci.yml`

CI runs on pull requests and on pushes to `main` or `master` when
`paylater_engineering/` or workflow files change.

The CI pipeline has seven jobs:

1. **Secret scanning**
   - Runs Gitleaks against the repository history.
   - Fails when committed credential-like material is detected.
   - Does not contain application credentials.
2. **Static security analysis**
   - Runs Bandit against Python application code.
   - Runs `pip-audit` against `docker/requirements.txt`.
3. **Python quality**
   - Uses Python 3.11.
   - Compiles `app/` and `database/`.
   - Installs the test runner.
   - Runs the repository test suite with `PYTHONPATH=.`.
   - PostgreSQL integration tests remain skipped unless a test DSN is
     explicitly provided; CI does not contain database credentials.
4. **Frontend quality**
   - Uses Node.js 20.
   - Runs `npm ci` from `app/frontend/`.
   - Runs the TypeScript/Vite production build.
5. **Compose validation**
   - Runs `docker compose config --quiet`.
   - Creates a temporary empty `.env` only because Compose declares that file
     through `env_file`; no credentials or secret values are stored in the
     workflow.
   - Validates Compose structure and variable interpolation without starting
     containers.
6. **Service integration**
   - Starts ephemeral PostgreSQL 16, Redis 7, and MinIO services.
   - Verifies a PostgreSQL query, Redis ping, and MinIO bucket operation.
   - Destroys the service containers when the job ends.
7. **Model training validation**
   - Reads the real Parquet dataset.
   - Verifies required targets and `borrower_id`.
   - Parses each training flow and verifies a training entry point exists.
   - Does not train production models in pull-request CI.

To reproduce the CI checks locally:

```bash
cd paylater_engineering
python3 -m compileall -q app database
PYTHONPATH=. pytest -q

cd app/frontend
npm ci
npm run build
cd ../..

docker compose config --quiet
```

Security and integration jobs use disposable CI-only values and services.
They do not access production databases, object storage, model registries, or
external API credentials.

### Pre-deployment delivery validation

Workflow: `.github/workflows/cd-pre.yml`

`cd-pre.yml` is the pre-deployment delivery workflow. It validates that the
current revision can produce deployable artifacts before the full deployment
workflow is used. It runs on pushes to `main` or `master`, version tags
matching `v*.*.*`, and manual dispatch:

1. Builds the FastAPI image locally in the GitHub Actions runner.
2. Starts the image and performs an API smoke test against `/docs`.
3. Installs frontend dependencies with `npm ci`.
4. Builds the frontend bundle with Vite.
5. Uploads the frontend `dist/` directory as a short-lived artifact.
6. Creates a commit-SHA release manifest describing the API image, frontend
   artifact, and rollback reference.

This workflow does not publish to GHCR, connect to staging or production, or
restart a production service. It is intended for pre-deployment verification
and artifact inspection.

### Full continuous delivery and deployment

Workflow: `.github/workflows/cd.yml`

`cd.yml` is the full deployment workflow. It publishes and deploys an
immutable release:

1. Builds the FastAPI image from `docker/api.Dockerfile`.
2. Publishes commit-SHA and ref tags to GitHub Container Registry.
3. Builds the frontend bundle and packages it as a commit-SHA archive.
4. Deploys the API image and frontend release to the protected `staging`
   Docker host over SSH.
5. Runs the staging `/health/` smoke test.
6. Deploys to the protected `production` environment when the workflow is
   manually dispatched for deployment or a version tag is pushed.
7. Applies required production environment reviewers before the production
   deployment proceeds.
8. Runs the production `/health/` smoke test.

The normal release sequence is:

```text
ci.yml -> cd-pre.yml -> cd.yml staging -> staging smoke test
       -> production approval -> cd.yml production -> production smoke test
```

`cd-pre.yml` and `cd.yml` may both be triggered by the same branch or tag
event. The pre-deployment workflow is a validation gate; the full workflow is
the workflow that publishes and deploys the release.

### Rollback strategy

Each delivery build is tied to an immutable commit SHA:

```text
paylater-fastapi:<commit-sha>
paylater-frontend-<commit-sha>
```

The release manifest is retained for 30 days. A deployment implementation
should retain the currently deployed SHA and roll back by redeploying the last
approved SHA with its matching frontend artifact. This avoids mutable
`latest` tags as rollback references.

The deployment workflow uses:

- **Container registry:** GitHub Container Registry (`ghcr.io`).
- **Deployment platform:** a Docker host or VM reachable through SSH.
- **Staging environment:** GitHub Environment named `staging`.
- **Production environment:** GitHub Environment named `production`.
- **Protected credentials:** GitHub Environment Secrets, never repository
  files.
- **Approval gate:** required reviewers configured on the `production`
  environment.

Configure these GitHub Environment values before enabling deployment:

| Environment | Variables | Secrets |
|---|---|---|
| `staging` | `APP_URL`, `APP_DIR` | `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT`, `DEPLOY_SSH_KEY` |
| `production` | `APP_URL`, `APP_DIR` | `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT`, `DEPLOY_SSH_KEY` |

`GITHUB_TOKEN` is supplied by GitHub Actions for GHCR authentication. It is
not written to the repository or release artifacts. Configure the production
environment with at least one required reviewer so a successful staging
smoke test does not automatically deploy to production.

The remote Docker host must already have Docker, a protected application
directory, and the production runtime `.env`. The workflow uploads only the
frontend release archive and pulls the immutable API image. It does not copy
runtime credentials to the host.

### Executing a rollback

1. Open **Actions → CD → Run workflow**.
2. Select `rollback` for `operation`.
3. Enter the full 40-character SHA of the previously approved release in
   `rollback_sha`.
4. Approve the `production` environment review.
5. The rollback job pulls the matching immutable GHCR image.
6. It restarts the API with the existing protected host `.env`.
7. It switches `current-frontend` to the retained frontend release directory.
8. It runs the production health smoke test.

The target release must still exist in the host's
`$APP_DIR/releases/<commit-sha>/dist` directory and the matching image must be
available in GHCR. Keep release directories and registry retention policies
long enough to support the required rollback window.

### Reading workflow results

1. Open the repository's **Actions** tab.
2. Select the `CI` or `CD` workflow run.
3. Inspect the failed job and step logs.
4. Reproduce the corresponding command locally.
5. Fix the source branch and push again.

CI/CD status is a quality signal, not proof that external services, model
artifacts, migrations, or production credentials are correctly configured.

## ⚠️ Current limitations and production-readiness checklist

The following items should be resolved before calling the platform production
ready:

1. **Migration review:** run and test the idempotent migration against a clean
   PostgreSQL volume before treating database initialization as production
   ready.
2. **API aggregation contract:** frontend pages for borrower directories,
   decisions, portfolio analytics, model governance, and audit require
   registered FastAPI endpoints. The frontend intentionally shows an
   unavailable state until those APIs exist.
3. **Authentication and authorization:** the frontend permission model is not
   a security boundary. Backend authentication, authorization, actor identity,
   and audit enforcement must be implemented and verified.
4. **Artifact loading contract:** training writes MinIO URIs, while serving
   currently resolves model versions through MLflow. The registry, MLflow
   model versions, and MinIO artifact paths must be connected and tested
   end-to-end.
5. **Source timestamps:** the dataset has no source event timestamp. Add an
   authoritative observation timestamp before relying on strict point-in-time
   training or feature joins.
6. **Secrets:** ensure MinIO credentials, database passwords, API keys, and
   other runtime secrets are managed outside source control.
7. **Container hardening:** pin image versions where appropriate, add least
   privilege, review exposed ports, and separate development bind mounts from
   production images.
8. **Operational tests:** run database, feature-store, model, serving, API,
   and monitoring integration tests against controlled environments.

## 📚 External technical references

The architecture uses the documented roles of these technologies:

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [FastAPI deployment with Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [MLflow tracking and artifact stores](https://mlflow.org/docs/latest/tracking/)
- [Prefect documentation](https://docs.prefect.io/)
- [Feast documentation](https://docs.feast.dev/)
- [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Redis documentation](https://redis.io/docs/)
