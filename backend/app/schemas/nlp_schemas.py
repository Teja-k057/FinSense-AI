from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=2, description="Financial news headline or article excerpt to analyze")
    source: Optional[str] = Field("AdHoc", description="Source identifier")
    ticker_hint: Optional[str] = Field(None, description="Optional ticker hint to guide entity extraction")

class EntityExtractionResult(BaseModel):
    ticker: str
    company_name: str
    sector: Optional[str] = "General"
    confidence: float = 1.0

class SentimentResult(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0, description="Normalized sentiment score from -1.0 to +1.0")
    label: str = Field(..., description="Positive, Negative, or Neutral")
    probabilities: Dict[str, float]
    explanation: Optional[str] = None

class EventClassificationResult(BaseModel):
    event_type: str = Field(..., description="Class from the controlled financial risk taxonomy")
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: Optional[str] = None
    severity_weight: float = 0.50

class RiskSignal(BaseModel):
    """
    Canonical structured RiskSignal schema required by the AI/NLP Risk Engine.
    Fields:
      - company
      - event_type
      - sentiment_score
      - impact_score
      - risk_level
      - explanation
      - source
      - timestamp
    """
    company: str = Field(..., description="Company ticker or identified entity name")
    event_type: str = Field(..., description="Controlled taxonomy classification")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Normalized sentiment in [-1.0, +1.0]")
    impact_score: float = Field(..., ge=1.0, le=10.0, description="Explainable impact score in [1.0, 10.0]")
    risk_level: str = Field(..., description="Categorical risk level: LOW, MEDIUM, HIGH, CRITICAL")
    explanation: str = Field(..., description="Explainable factor breakdown justifying the signal")
    source: str = Field(..., description="Ingestion source (GDELT, Kaggle, AdHoc, etc.)")
    timestamp: datetime = Field(default_factory=utc_now, description="UTC event timestamp")

    # Additional enrichments for downstream module support
    id: Optional[str] = None
    document_id: Optional[str] = None
    title: Optional[str] = None
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    sector: Optional[str] = "General"
    confidence: float = 1.0
    sentiment_label: Optional[str] = None
    factor_breakdown: Dict[str, Any] = Field(default_factory=dict)
    is_duplicate: bool = False

    @model_validator(mode="before")
    @classmethod
    def harmonize_aliases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Harmonize company / ticker
            if "company" not in values and "ticker" in values:
                values["company"] = values["ticker"]
            elif "ticker" not in values and "company" in values:
                values["ticker"] = values["company"]

            # Harmonize timestamp / created_at / published_at
            if "timestamp" not in values:
                if "created_at" in values and values["created_at"]:
                    values["timestamp"] = values["created_at"]
                elif "published_at" in values and values["published_at"]:
                    values["timestamp"] = values["published_at"]
                elif "publication_time" in values and values["publication_time"]:
                    values["timestamp"] = values["publication_time"]
                else:
                    values["timestamp"] = utc_now()

            # Harmonize document_id / article_id
            if "document_id" not in values and "article_id" in values:
                values["document_id"] = values["article_id"]

        return values

    @property
    def created_at(self) -> datetime:
        return self.timestamp

class RiskSignalResponse(BaseModel):
    """API response model for risk signal queries."""
    id: Optional[int] = None
    article_id: Optional[str] = None
    ticker: str
    company_name: Optional[str] = None
    sentiment_score: float
    sentiment_label: str
    event_type: str
    event_confidence: float
    impact_score: float = Field(..., ge=1.0, le=10.0)
    risk_level: Optional[str] = "MEDIUM"
    summary: Optional[str] = None
    explanation: Optional[str] = None
    created_at: Optional[datetime] = None

class IngestionBatchResponse(BaseModel):
    source: str
    total_articles: int
    signals_generated: int
    signals: List[RiskSignal] = []
