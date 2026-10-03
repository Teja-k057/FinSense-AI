import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship, synonym
from .connection import Base

def utc_now():
    return datetime.now(timezone.utc)

# -----------------------------------------------------------------------------
# 1. NewsDocument (Canonical News Ingestion Model)
# -----------------------------------------------------------------------------
class NewsDocument(Base):
    __tablename__ = "news_documents"

    id = Column(String(64), primary_key=True, index=True, comment="Deterministic SHA-256 hash")
    source = Column(String(32), nullable=False, index=True)  # 'GDELT' or 'Kaggle'
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    publication_time = Column(DateTime, nullable=False, default=utc_now, index=True)
    retrieved_time = Column(DateTime, nullable=False, default=utc_now, index=True)
    company_entities = Column(Text, nullable=True)  # JSON-serialized list of tickers
    original_label = Column(String(64), nullable=True)
    domain = Column(String(128), nullable=True, default="Unknown")
    language = Column(String(32), nullable=True, default="English")
    query_used = Column(String(256), nullable=True)
    metadata_json = Column(Text, nullable=True)

    # Relationships
    signals = relationship("RiskSignal", back_populates="document", cascade="all, delete-orphan")

    # Backwards-compatibility aliases
    content = synonym("text")
    published_at = synonym("publication_time")
    ingested_at = synonym("retrieved_time")

# Alias for backwards compatibility with earlier steps
Article = NewsDocument


# -----------------------------------------------------------------------------
# 2. RiskSignal (Structured AI/NLP Risk Signals)
# -----------------------------------------------------------------------------
class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    document_id = Column(String(64), ForeignKey("news_documents.id"), nullable=True, index=True)
    article_id = Column(String(64), nullable=True)  # Backwards compatibility alias
    company = Column(String(16), nullable=False, index=True)  # Ticker symbol
    ticker = Column(String(16), nullable=False, index=True)   # Ticker alias
    company_name = Column(String(128), nullable=True)
    sector = Column(String(64), nullable=True, default="General")
    sentiment_score = Column(Float, nullable=False)  # [-1.0, +1.0]
    sentiment_label = Column(String(16), nullable=False)  # Positive, Negative, Neutral
    event_type = Column(String(64), nullable=False, index=True)  # 10-class taxonomy
    event_confidence = Column(Float, nullable=False, default=0.0)
    impact_score = Column(Float, nullable=False, index=True)  # [1.0, 10.0]
    risk_level = Column(String(16), nullable=False, default="MEDIUM", index=True)
    explanation = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # Alias
    source = Column(String(32), nullable=False, default="GDELT", index=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)

    # Relationships
    document = relationship("NewsDocument", back_populates="signals")

    @property
    def article(self):
        return self.document

# Composite index for multi-column queries
Index("ix_risk_signals_company_time", RiskSignal.company, RiskSignal.timestamp)
Index("ix_risk_signals_event_impact", RiskSignal.event_type, RiskSignal.impact_score)

# -----------------------------------------------------------------------------
# 3. Company (Index & Universe Master Data)
# -----------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    ticker = Column(String(16), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    sector = Column(String(64), nullable=False, index=True)
    industry = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    constituents = relationship("IndexConstituent", back_populates="company_info")
    market_records = relationship("MarketData", back_populates="company_info")

# -----------------------------------------------------------------------------
# 4. IndexConstituent (Mock Index Holdings & Weights)
# -----------------------------------------------------------------------------
class IndexConstituent(Base):
    __tablename__ = "index_constituents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_name = Column(String(64), nullable=False, default="S&P x CRISIL 15", index=True)
    ticker = Column(String(16), ForeignKey("companies.ticker"), nullable=False, index=True)
    baseline_weight = Column(Float, nullable=False, default=0.0667)
    current_weight = Column(Float, nullable=False, default=0.0667)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, index=True)

    # Relationships
    company_info = relationship("Company", back_populates="constituents")

# -----------------------------------------------------------------------------
# 5. MarketData (Historical & Real-Time Price/Return Snapshots)
# -----------------------------------------------------------------------------
class MarketData(Base):
    __tablename__ = "market_data_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), ForeignKey("companies.ticker"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    previous_close = Column(Float, nullable=True)
    change_pct = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    volatility_annual = Column(Float, nullable=True)
    beta = Column(Float, default=1.0)
    as_of = Column(DateTime, nullable=False, default=utc_now, index=True)
    retrieved_at = Column(DateTime, nullable=False, default=utc_now, index=True)

    # Relationships
    company_info = relationship("Company", back_populates="market_records")

# -----------------------------------------------------------------------------
# 6. RebalanceRun (Module A Execution Auditing Header)
# -----------------------------------------------------------------------------
class RebalanceRun(Base):
    __tablename__ = "rebalance_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    universe_size = Column(Integer, nullable=False, default=15)
    turnover_pct = Column(Float, nullable=False, default=0.0)
    total_current_weight_pct = Column(Float, nullable=False, default=100.0)
    total_target_weight_pct = Column(Float, nullable=False, default=100.0)
    average_sentiment = Column(Float, nullable=False, default=0.0)
    average_impact = Column(Float, nullable=False, default=5.0)
    methodology = Column(Text, nullable=True)

    # Relationships
    decisions = relationship("RebalanceDecision", back_populates="run", cascade="all, delete-orphan")

# -----------------------------------------------------------------------------
# 7. RebalanceDecision (Constituent Tactical Allocation Decisions)
# -----------------------------------------------------------------------------
class RebalanceDecision(Base):
    __tablename__ = "rebalance_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("rebalance_runs.id"), nullable=False, index=True)
    ticker = Column(String(16), nullable=False, index=True)
    company_name = Column(String(128), nullable=True)
    current_weight = Column(Float, nullable=False)
    target_weight = Column(Float, nullable=False)
    weight_delta_pct = Column(Float, nullable=False)
    action = Column(String(16), nullable=False, index=True)  # 'INCREASE', 'HOLD', 'REDUCE'
    sentiment_score = Column(Float, nullable=False, default=0.0)
    impact_score = Column(Float, nullable=False, default=5.0)
    event_type = Column(String(64), nullable=False, default="Other", index=True)
    explanation = Column(Text, nullable=False)

    # Relationships
    run = relationship("RebalanceRun", back_populates="decisions")

# -----------------------------------------------------------------------------
# 8. DataSourceLog (Audit Trail for Automatic Ingestion)
# -----------------------------------------------------------------------------
class DataSourceLog(Base):
    __tablename__ = "data_source_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32), nullable=False, index=True)  # 'GDELT', 'Kaggle', 'yfinance'
    status = Column(String(32), nullable=False, index=True)  # 'SUCCESS_LIVE', 'SUCCESS_CACHED', 'ERROR'
    record_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)
    query_used = Column(String(256), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)

# -----------------------------------------------------------------------------
# Legacy / Backward Compatibility (Discontinued Module B Stress Test Run)
# -----------------------------------------------------------------------------
class StressTestRun(Base):
    __tablename__ = "stress_test_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(String(64), nullable=False, default="default")
    scenario_type = Column(String(64), nullable=False)
    scenario_name = Column(String(128), nullable=True)
    base_portfolio_value = Column(Float, nullable=False, default=10000000.0)
    stressed_portfolio_value = Column(Float, nullable=False, default=10000000.0)
    pnl_loss_amount = Column(Float, nullable=False, default=0.0)
    pnl_loss_pct = Column(Float, nullable=False, default=0.0)
    pre_var_95 = Column(Float, nullable=True)
    post_var_95 = Column(Float, nullable=True)
    pre_cvar_95 = Column(Float, nullable=True)
    post_cvar_95 = Column(Float, nullable=True)
    metrics_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

__all__ = [
    "NewsDocument",
    "RiskSignal",
    "Company",
    "IndexConstituent",
    "MarketData",
    "RebalanceRun",
    "RebalanceDecision",
    "DataSourceLog",
    "StressTestRun",
]

