from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class NewsDocument(BaseModel):
    """
    Canonical normalized NewsDocument schema shared across GDELT and Kaggle Financial News.
    Ensures the downstream AI/NLP Risk Engine processes identical contracts regardless of source.
    """
    id: str = Field(..., description="Unique deterministic SHA-256 hash")
    source: str = Field(..., description="Data source name: GDELT or Kaggle")
    title: str = Field(..., min_length=2, description="Sanitized headline or title")
    text: str = Field(..., min_length=2, description="Cleaned full text or article lead body")
    url: Optional[str] = Field(None, description="Canonical article web link")
    publication_time: datetime = Field(default_factory=utc_now, description="UTC publication timestamp")
    retrieved_time: datetime = Field(default_factory=utc_now, description="UTC ingestion timestamp")
    company_entities: List[str] = Field(default_factory=list, description="Resolved company names or ticker candidates")
    original_label: Optional[str] = Field(None, description="Original ground-truth label if provided by dataset")
    domain: Optional[str] = Field("Unknown", description="Publisher or domain name")
    language: Optional[str] = Field("English", description="Article language")
    query_used: Optional[str] = Field(None, description="Search query or keyword used if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific extra properties")

    @model_validator(mode="before")
    @classmethod
    def harmonize_field_aliases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Harmonize publication time
            if "published_at" in values and "publication_time" not in values:
                values["publication_time"] = values["published_at"]
            # Harmonize retrieved time
            if "retrieved_at" in values and "retrieved_time" not in values:
                values["retrieved_time"] = values["retrieved_at"]
            # Harmonize text / content
            if "raw_text" in values and "text" not in values:
                values["text"] = values["raw_text"]
            elif "content" in values and "text" not in values:
                values["text"] = values["content"]
            elif "title" in values and "text" not in values:
                values["text"] = values["title"]
        return values

    # Backwards-compatibility properties
    @property
    def published_at(self) -> datetime:
        return self.publication_time

    @property
    def retrieved_at(self) -> datetime:
        return self.retrieved_time

    @property
    def raw_text(self) -> str:
        return self.text

# Alias for backwards-compatibility
ArticleRecord = NewsDocument

class MarketDataQuote(BaseModel):
    """Normalized schema for ticker market data retrieved via yfinance."""
    ticker: str
    price: float = Field(..., gt=0.0)
    change_pct: float = 0.0
    market_cap: Optional[float] = None
    trailing_pe: Optional[float] = None
    volume: Optional[int] = None
    volatility_annual: float = 0.25
    beta: float = 1.0
    is_fallback: bool = False
    status: str = "LIVE"
    acquired_at: datetime = Field(default_factory=utc_now)

class AcquisitionSummary(BaseModel):
    """Standardized summary returned by all ingestion adapters."""
    source: str
    record_count: int
    status: str  # SUCCESS_LIVE, SUCCESS_CACHED, EMPTY, ERROR
    is_fallback: bool = False
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    query_used: Optional[str] = None
    acquired_at: datetime = Field(default_factory=utc_now)
    records: List[Any] = Field(default_factory=list)
