import os
from pathlib import Path
from dotenv import load_dotenv

DIR_PATH = Path(__file__).parents[2]
ENV_PATH = DIR_PATH / ".env"
load_dotenv(ENV_PATH)

class Settings():

    # PostgreSQL
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    POSTGRES_SCHEMA: str = os.getenv("POSTGRES_SCHEMA")
    POSTGRES_TABLE: str = os.getenv("POSTGRES_TABLE")
    POSTGRES_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Data source selector
    DATA_SOURCE: str = os.getenv("DATA_SOURCE")

    # Inference cache
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "10000"))

    # LLM API Keys
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    NINEROUTER_BASE_URL: str = os.getenv("NINEROUTER_BASE_URL", "http://host.docker.internal:20128/v1")
    NINEROUTER_API_KEY: str = os.getenv("NINEROUTER_API_KEY")
    NINEROUTER_MODEL_NAME: str = os.getenv("NINEROUTER_MODEL_NAME", "sragent")

    # ML Path dependencies
    BASE_PATH: Path = Path(__file__).parents[2] # paylater_engineering/
    DATABASE_PATH: Path = BASE_PATH / "database" / "dataset"
    ML_MODEL_PATH: Path = DATABASE_PATH / "model_artifacts"
    LLM_PATH: Path = DATABASE_PATH / "llm_artifacts"
    DATA_PATH: Path = DATABASE_PATH / "indonesia_fintech_paylater.parquet"

    # JSON Parse
    #ROLE_CONFIG: Path = DATABASE_PATH / "llm_artifacts" / "role_config.json"

    # ── Storage ──
    MINIO_ENDPOINT   = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
    MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
    MINIO_BUCKET     = os.getenv("MINIO_BUCKET")

    # ── MLflow ──
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    MLFLOW_EXPERIMENT : str = os.getenv("MLFLOW_EXPERIMENT", "paylater_indodana_model")

    # ── Feast ──
    #FEAST_REPO_PATH = Path("feature_store")

settings = Settings()