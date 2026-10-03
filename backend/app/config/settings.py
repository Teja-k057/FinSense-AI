from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI/NLP Risk Engine and Tactical Stock Index Rebalancer"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # Database
    DATABASE_URL: str = "sqlite:///./data/risk_engine.db"
    POSTGRES_FALLBACK_SQLITE: bool = True

    # Directories
    DATA_DIR: Path = BASE_DIR / "data"
    GDELT_CACHE_DIR: Path = BASE_DIR / "data" / "gdelt_cache"
    KAGGLE_DIR: Path = BASE_DIR / "data" / "kaggle"
    MARKET_CACHE_DIR: Path = BASE_DIR / "data" / "market_cache"

    # Ingestion: GDELT
    GDELT_API_BASE: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    GDELT_TIMEOUT_SECONDS: int = 8
    GDELT_MAX_RETRIES: int = 2
    GDELT_MAX_RECORDS: int = 50

    # Ingestion: Kaggle Financial News
    KAGGLE_PUBLIC_DATASET_URL: str = "https://raw.githubusercontent.com/isaaccs/sentiment-analysis-for-financial-news/master/all-data.csv"
    KAGGLE_CACHE_FILE: Path = BASE_DIR / "data" / "kaggle" / "financial_phrasebank.csv"
    KAGGLE_USERNAME: Optional[str] = None
    KAGGLE_KEY: Optional[str] = None

    # Ingestion: yfinance Market Data
    YFINANCE_CACHE_TTL_HOURS: int = 12

    # NLP / Financial Models
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"
    USE_LOCAL_TRANSFORMERS: bool = False
    FALLBACK_EXPLAINABLE_NLP: bool = True

    # Risk Engine: Configurable Impact Scorer Factor Weights (Sum = 1.0)
    IMPACT_WEIGHT_EVENT_SEVERITY: float = 0.30
    IMPACT_WEIGHT_SENTIMENT_MAGNITUDE: float = 0.25
    IMPACT_WEIGHT_CATEGORY_RISK: float = 0.20
    IMPACT_WEIGHT_ENTITY_RELEVANCE: float = 0.15
    IMPACT_WEIGHT_MARKET_SENSITIVITY: float = 0.10

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure required directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.GDELT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
settings.MARKET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
