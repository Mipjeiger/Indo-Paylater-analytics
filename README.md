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
- **Redis Commander** — local Redis inspection interface.
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

The source dataset is
`database/dataset/indonesia_fintech_paylater.parquet`. The inspected dataset
contains 10,000 rows and 30 columns, including:

- borrower demographics and employment attributes;
- income and regional minimum wage information;
- loan tenor, interest, credit-limit, and installment measures;
- DTI, debt-service, utilization, and disposable-income indicators;
- TWP90/default status;
- root-cause labels; and
- derived risk fields.

The dataset has no source timestamp column and no missing values in the
inspected file. `borrower_id` is unique in that dataset and is the natural
entity key. Because there is no event timestamp in the source data, temporal
model evaluation currently uses deterministic ordering where the training
flow requires a temporal split. A true production temporal split requires an
authoritative observation or event timestamp.

The current model tasks are:

| Task | Model | Target/output | Important leakage controls |
|---|---|---|---|
| TWP90 | CatBoost classifier | Binary default indicator derived from `twp90_default_status` | Excludes target, root cause, risk outputs, rationale, and `days_past_due` |
| DTI/distress | TensorFlow/Keras multi-output regression | `debt_to_income_ratio`, `financial_distress_index` | Excludes both targets, `total_loan_outstanding_idr`, risk outputs, and delinquency fields |
| Root cause | LightGBM multiclass classifier | `primary_default_root_cause` | Excludes the root-cause target, TWP90 target, risk outputs, and rationale |

Model training flows upload artifacts to the configured MinIO/S3-compatible
bucket. Temporary files are used only for model serialization during upload;
the training flows do not intentionally maintain a persistent local model
directory.

## 🏗️ Architecture

```text
                         +----------------------+
                         | React/Vite frontend   |
                         | app/frontend         |
                         +----------+-----------+
                                    |
                                    | HTTP / JSON
                                    v
+-------------------+     +--------+---------+     +----------------------+
| PostgreSQL 16     |<--->| FastAPI/Uvicorn  |<--->| MLflow tracking      |
| data + registry   |     | app/api          |     | metadata + artifacts |
+-------------------+     +--------+---------+     +----------+-----------+
                                    |                         |
                                    v                         v
                         +----------+---------+     +---------+----------+
                         | Model serving      |     | MinIO              |
                         | app/serving        |     | S3-compatible store|
                         +--------------------+     +--------------------+

       +------------------+       +--------------------+
       | Feast             |<----->| Redis online store|
       | offline/online   |       +--------------------+
       +--------+---------+
                |
                v
       +------------------+
       | Prefect workflows|
       | training flows  |
       +------------------+

       +------------------+       +------------------+
       | Prometheus       |<------| FastAPI /metrics |
       +--------+---------+       +------------------+
                |
                v
       +------------------+
       | Grafana          |
       +------------------+
```

### 🔌 Service responsibilities

| Service | Compose port | Responsibility |
|---|---:|---|
| PostgreSQL | `5432` | Source data, model metadata, predictions, actions, and drift reports |
| Redis | `6379` | Cache and Feast online-store backend |
| Redis Commander | `8081` | Local Redis inspection UI |
| MinIO API | `9000` | S3-compatible model/artifact storage |
| MinIO Console | `9001` | Local object-storage UI |
| FastAPI | `8000` | Health, metrics, scoring, and classification HTTP boundary |
| MLflow | `5000` | Experiment tracking, model metadata, and artifact serving |
| Prefect | `4200` | Workflow orchestration server |
| Prometheus | `9090` | Pull-based metrics collection |
| Grafana | `3000` | Metrics visualization |
| Frontend dev server | `5173` | Vite React application when run locally |

All Compose services use the `paylater_indodana` bridge network. Persistent
state is stored in named volumes: `pgdata`, `minio_data`, `mlflow_data`,
`prefect_data`, `prometheus_data`, and `grafana_data`.

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

The migration must be reviewed before relying on a clean initialization. The
current SQL creates `paylater.data`, while some existing index statements
still reference `paylater.database`; correct that mismatch before treating
migration execution as production-ready.

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

### 5. 🧩 Build and start Feast

Feast is built from
[`docker/feast.Dockerfile`](paylater_engineering/docker/feast.Dockerfile).
The image installs Feast `0.41.0`, copies the project into `/app`, and uses
the PostgreSQL-backed source and Redis online store defined in
`app/feast/feature_store.yaml`.

The Feast image is currently standalone and is not a service in
`docker-compose.yml`. Build it from the `paylater_engineering` directory so
the Dockerfile's `COPY . /app` includes the full project:

```bash
docker build \
  --file docker/feast.Dockerfile \
  --tag paylater-feast:0.41.0 \
  .
```

Apply entity, source, and feature-view definitions before starting the service.
The command below creates or updates the local Feast registry:

```bash
docker run --rm \
  --network paylater_indodana \
  --env POSTGRES_HOST=postgres \
  --env POSTGRES_PORT=5432 \
  --env POSTGRES_DB="$POSTGRES_DB" \
  --env POSTGRES_USER="$POSTGRES_USER" \
  --env POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --env REDIS_URL=redis://redis:6379/0 \
  paylater-feast:0.41.0 \
  sh -c 'cd app/feast && feast apply'
```

Start Feast on port `6566` and attach it to the same Compose network so it can
resolve the `postgres` and `redis` service names:

```bash
docker run --rm \
  --name paylater-feast \
  --network paylater_indodana \
  --publish 6566:6566 \
  --env POSTGRES_HOST=postgres \
  --env POSTGRES_PORT=5432 \
  --env POSTGRES_DB="$POSTGRES_DB" \
  --env POSTGRES_USER="$POSTGRES_USER" \
  --env POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --env REDIS_URL=redis://redis:6379/0 \
  paylater-feast:0.41.0
```

In another terminal, verify the Feast process:

```bash
docker logs --follow paylater-feast
```

The default `provider: local` registry is stored at
`app/feast/data/registry.db` inside the container. For local development,
persist it by mounting a host directory and rerun `feast apply`:

```bash
mkdir -p .feast-data
docker run --rm \
  --network paylater_indodana \
  --volume "$PWD/.feast-data:/app/app/feast/data" \
  --env POSTGRES_HOST=postgres \
  --env POSTGRES_PORT=5432 \
  --env POSTGRES_DB="$POSTGRES_DB" \
  --env POSTGRES_USER="$POSTGRES_USER" \
  --env POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --env REDIS_URL=redis://redis:6379/0 \
  paylater-feast:0.41.0 \
  sh -c 'cd app/feast && feast apply'
```

Apply feast for materialize feature store data
```bash
docker exec -it feast sh -c "cd app/feast && feast apply”
```

To access Feast UI use this docker code definitely
```bash
docker exec -it feast sh -c "cd app/feast && feast ui --port 8888”
```

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

- `paylater.data`: source borrower and loan features;
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

1. **Migration review:** the current migration creates `paylater.data` but
   still contains index statements targeting `paylater.database`. Correct and
   test the migration before a clean PostgreSQL initialization.
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
