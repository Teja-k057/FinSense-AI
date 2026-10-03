import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database.connection import get_db
from backend.app.database.models import Article, RiskSignal as DBRiskSignal
from backend.app.schemas.nlp_schemas import (
    RiskSignal,
    TextAnalysisRequest
)
from backend.app.schemas.common import APIResponse
from backend.app.risk_engine.signals import RiskSignalEngine
from backend.app.nlp.event_classifier import FinancialEventClassifier
from backend.app.nlp.impact_scorer import FinancialImpactScorer
from backend.app.portfolio.market_data import MarketDataService
from pydantic import BaseModel, Field

logger = logging.getLogger("api.routes_risk")

router = APIRouter()
risk_engine = RiskSignalEngine()
market_service = MarketDataService()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# ---------------------------------------------------------
# Pydantic Schemas for API Documentation & Validation
# ---------------------------------------------------------

class HealthCheckComponents(BaseModel):
    database: str
    sentiment_engine: str
    event_classifier: str
    impact_scorer: str

class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "AI/NLP Risk Engine"
    timestamp: datetime = Field(default_factory=utc_now)
    components: HealthCheckComponents

class NewsArticleItem(BaseModel):
    id: str
    source: str
    title: str
    text: str
    url: Optional[str] = None
    publication_time: datetime
    retrieved_time: datetime
    company_entities: List[str] = []
    domain: Optional[str] = "Unknown"
    language: Optional[str] = "English"
    original_label: Optional[str] = None

class PaginatedNewsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[NewsArticleItem]

class PaginatedRiskSignalResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[RiskSignal]

class CompanyRiskSignalSummary(BaseModel):
    company: str
    company_name: str
    sector: str
    total_signals: int
    average_sentiment: float
    average_impact: float
    highest_risk_level: str
    event_distribution: Dict[str, int]
    signals: List[RiskSignal]

class CompanyListItem(BaseModel):
    ticker: str
    name: str
    sector: str
    market_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    base_weight_pct: float = 6.67
    signal_count: int = 0
    average_sentiment: float = 0.0
    average_impact: float = 5.0
    risk_level: str = "LOW"

class EventTypeItem(BaseModel):
    event_type: str
    description: str
    severity_weight: float
    signal_count: int = 0

EVENT_DESCRIPTIONS: Dict[str, str] = {
    "Geopolitical": "International conflicts, tariffs, trade wars, defense actions, sanctions, and national security disruptions.",
    "Macroeconomic": "Monetary policy decisions, interest rate changes, inflation/CPI metrics, GDP reports, and central bank commentary.",
    "Credit Event": "Corporate debt distress, debt defaults, rating downgrades, insolvency, liquidity shortfalls, and bankruptcy risks.",
    "Merger/Acquisition": "M&A transactions, corporate takeovers, buyouts, divestitures, spin-offs, and consolidation agreements.",
    "Product Launch": "New product rollouts, commercial releases, technology unveilings, patent filings, and innovation milestones.",
    "Regulatory": "Antitrust enforcement, legal investigations, SEC/DOJ probes, regulatory compliance penalties, and court rulings.",
    "Earnings": "Quarterly earnings results, revenue and net income performance, profit margins, guidance forecasts, and dividend actions.",
    "Supply Chain": "Manufacturing constraints, supply bottlenecks, factory shutdowns, logistics disruptions, and component shortages.",
    "Cybersecurity": "Ransomware attacks, enterprise data breaches, infrastructure hacks, software vulnerabilities, and unauthorized access.",
    "Other": "General corporate and economic news without specific trigger keywords."
}

# ---------------------------------------------------------
# Helper: Map DB row to Canonical RiskSignal
# ---------------------------------------------------------
def _map_db_to_signal(s: DBRiskSignal, db: Session) -> RiskSignal:
    canonical_event = s.event_type
    # Map legacy categories to 10-class taxonomy if found in DB
    legacy_map = {
        "Credit & Liquidity Distress": "Credit Event",
        "Regulatory & Legal Penalties": "Regulatory",
        "Earnings & Financial Performance": "Earnings",
        "M&A and Corporate Restructuring": "Merger/Acquisition",
        "Supply Chain & Operational Disruption": "Supply Chain",
        "Macroeconomic & Monetary Policy": "Macroeconomic"
    }
    canonical_event = legacy_map.get(canonical_event, canonical_event)
    if canonical_event not in FinancialEventClassifier.CONTROLLED_TAXONOMY:
        canonical_event = "Other"

    # Derive source
    source = "GDELT"
    if s.article_id:
        art = db.query(Article).filter(Article.id == s.article_id).first()
        if art and art.source:
            source = art.source

    # Derive risk level
    risk_level = FinancialImpactScorer.determine_risk_level(s.impact_score, s.sentiment_score, canonical_event)

    # Explanation
    explanation = s.summary or (
        f"Signal for {s.ticker} ({s.company_name or 'N/A'}). Event: {canonical_event}. "
        f"Sentiment: {s.sentiment_label} ({s.sentiment_score:+.2f}). "
        f"Impact Score: {s.impact_score}/10 [Risk Level: {risk_level}]."
    )

    return RiskSignal(
        company=s.ticker,
        event_type=canonical_event,
        sentiment_score=round(s.sentiment_score, 4),
        impact_score=round(s.impact_score, 1),
        risk_level=risk_level,
        explanation=explanation,
        source=source,
        timestamp=s.created_at or utc_now(),
        id=str(s.id),
        document_id=s.article_id,
        ticker=s.ticker,
        company_name=s.company_name or s.ticker,
        confidence=s.event_confidence,
        sentiment_label=s.sentiment_label
    )

# ---------------------------------------------------------
# 1. GET /health
# ---------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational status of the Risk Engine, database, and NLP components."
)
def get_health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(func.now())
    except Exception as e:
        logger.error(f"[Health] Database connection error: {e}")
        db_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service="AI/NLP Risk Engine & Tactical High-Frequency Rebalancer",
        timestamp=utc_now(),
        components=HealthCheckComponents(
            database=db_status,
            sentiment_engine="operational",
            event_classifier="operational",
            impact_scorer="operational"
        )
    )

# ---------------------------------------------------------
# 2. GET /news
# ---------------------------------------------------------
@router.get(
    "/news",
    response_model=PaginatedNewsResponse,
    summary="Get Ingested News Articles",
    description="Retrieves ingested news articles from GDELT and Kaggle with multi-criteria filtering and pagination."
)
def get_news(
    company: Optional[str] = Query(None, description="Filter by company ticker (e.g., AAPL)"),
    source: Optional[str] = Query(None, description="Filter by source: GDELT or Kaggle"),
    query: Optional[str] = Query(None, description="Keyword search in title or text"),
    start_date: Optional[datetime] = Query(None, description="Filter articles published on or after (ISO-8601 UTC)"),
    end_date: Optional[datetime] = Query(None, description="Filter articles published on or before (ISO-8601 UTC)"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (1–100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    q = db.query(Article)

    if source:
        q = q.filter(Article.source.ilike(source.strip()))
    if query:
        q = q.filter(Article.title.ilike(f"%{query.strip()}%"))
    if start_date:
        q = q.filter(Article.published_at >= start_date)
    if end_date:
        q = q.filter(Article.published_at <= end_date)

    # If company filter requested, join with signals
    if company:
        q = q.join(DBRiskSignal, Article.id == DBRiskSignal.article_id).filter(
            DBRiskSignal.ticker == company.upper().strip()
        )

    total_count = q.distinct().count()
    articles = q.order_by(Article.published_at.desc()).offset(offset).limit(limit).all()

    items = []
    for a in articles:
        # Extract associated ticker entities
        tickers = [sig.ticker for sig in a.signals] if a.signals else []
        items.append(
            NewsArticleItem(
                id=a.id,
                source=a.source,
                title=a.title,
                text=a.content or a.title,
                url=a.url,
                publication_time=a.published_at,
                retrieved_time=a.ingested_at,
                company_entities=tickers,
                domain="reuters.com" if "reuters" in (a.url or "") else "financial-news",
                language="English"
            )
        )

    return PaginatedNewsResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        items=items
    )

# ---------------------------------------------------------
# 3. GET /risk-signals
# ---------------------------------------------------------
@router.get(
    "/risk-signals",
    response_model=PaginatedRiskSignalResponse,
    summary="Get Structured Risk Signals",
    description="Retrieves structured risk signals with multi-criteria filtering by company, event, risk level, and source."
)
def get_risk_signals(
    company: Optional[str] = Query(None, description="Filter by stock ticker symbol (e.g., NVDA, MSFT)"),
    event_type: Optional[str] = Query(None, description="Filter by event category from 10-class taxonomy"),
    source: Optional[str] = Query(None, description="Filter by source (GDELT, Kaggle, AdHoc)"),
    risk_level: Optional[str] = Query(None, description="Filter by categorical risk level: CRITICAL, HIGH, MEDIUM, LOW"),
    min_impact: Optional[float] = Query(1.0, ge=1.0, le=10.0, description="Minimum impact score (1.0–10.0)"),
    max_impact: Optional[float] = Query(10.0, ge=1.0, le=10.0, description="Maximum impact score (1.0–10.0)"),
    min_sentiment: Optional[float] = Query(-1.0, ge=-1.0, le=1.0, description="Minimum sentiment score (-1.0 to +1.0)"),
    max_sentiment: Optional[float] = Query(1.0, ge=-1.0, le=1.0, description="Maximum sentiment score (-1.0 to +1.0)"),
    start_date: Optional[datetime] = Query(None, description="Earliest signal timestamp"),
    end_date: Optional[datetime] = Query(None, description="Latest signal timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Page limit (1–200)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    q = db.query(DBRiskSignal).filter(
        DBRiskSignal.impact_score >= min_impact,
        DBRiskSignal.impact_score <= max_impact,
        DBRiskSignal.sentiment_score >= min_sentiment,
        DBRiskSignal.sentiment_score <= max_sentiment
    )

    if company:
        q = q.filter(DBRiskSignal.ticker == company.upper().strip())
    if event_type:
        q = q.filter(DBRiskSignal.event_type.ilike(event_type.strip()))
    if start_date:
        q = q.filter(DBRiskSignal.created_at >= start_date)
    if end_date:
        q = q.filter(DBRiskSignal.created_at <= end_date)

    total_count = q.count()
    rows = q.order_by(DBRiskSignal.created_at.desc()).offset(offset).limit(limit).all()

    signals: List[RiskSignal] = []
    for r in rows:
        sig = _map_db_to_signal(r, db)
        if source and sig.source.lower() != source.strip().lower():
            continue
        if risk_level and sig.risk_level.upper() != risk_level.strip().upper():
            continue
        signals.append(sig)

    return PaginatedRiskSignalResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        items=signals
    )

# ---------------------------------------------------------
# 4. GET /risk-signals/{company}
# ---------------------------------------------------------
@router.get(
    "/risk-signals/{company}",
    response_model=CompanyRiskSignalSummary,
    summary="Get Risk Signals for a Specific Company",
    description="Returns aggregated risk metrics and structured signal history for an individual company ticker."
)
def get_company_risk_signals(
    company: str = Path(..., description="Stock ticker symbol (e.g., AAPL, NVDA, JPM)"),
    limit: int = Query(50, ge=1, le=200, description="Number of recent signals to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    ticker = company.upper().strip()
    company_info = MarketDataService.DEFAULT_INDEX_UNIVERSE.get(ticker, {
        "name": ticker,
        "sector": "General"
    })

    q = db.query(DBRiskSignal).filter(DBRiskSignal.ticker == ticker)
    total_signals = q.count()

    if total_signals == 0:
        # Check if valid ticker in universe; if yes return zero-state gracefully
        if ticker not in MarketDataService.DEFAULT_INDEX_UNIVERSE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{company}' was not found in active universe."
            )

    rows = q.order_by(DBRiskSignal.created_at.desc()).offset(offset).limit(limit).all()
    signals = [_map_db_to_signal(r, db) for r in rows]

    if signals:
        avg_sent = round(sum(s.sentiment_score for s in signals) / len(signals), 4)
        avg_imp = round(sum(s.impact_score for s in signals) / len(signals), 1)
        # Distribution
        dist: Dict[str, int] = {}
        for s in signals:
            dist[s.event_type] = dist.get(s.event_type, 0) + 1

        highest_risk = "LOW"
        risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        for s in signals:
            if risk_hierarchy.get(s.risk_level, 1) > risk_hierarchy.get(highest_risk, 1):
                highest_risk = s.risk_level
    else:
        avg_sent = 0.0
        avg_imp = 5.0
        dist = {}
        highest_risk = "LOW"

    return CompanyRiskSignalSummary(
        company=ticker,
        company_name=company_info["name"],
        sector=company_info["sector"],
        total_signals=total_signals,
        average_sentiment=avg_sent,
        average_impact=avg_imp,
        highest_risk_level=highest_risk,
        event_distribution=dist,
        signals=signals
    )

# ---------------------------------------------------------
# 5. POST /analyze
# ---------------------------------------------------------
@router.post(
    "/analyze",
    response_model=RiskSignal,
    summary="Analyze Financial Text for Risk Signals",
    description="Accepts arbitrary financial news text, runs the unified NLP Risk Engine, and returns an explainable RiskSignal."
)
def analyze_text(
    payload: TextAnalysisRequest,
    persist: bool = Query(False, description="Persist generated signal to database"),
    db: Session = Depends(get_db)
):
    try:
        signal = risk_engine.process_text(
            raw_text=payload.text,
            source=payload.source or "AdHoc",
            ticker_hint=payload.ticker_hint,
            db=db if persist else None
        )
        return signal
    except Exception as e:
        logger.error(f"[Analyze] Error analyzing text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk Engine inference failed: {str(e)}"
        )

# ---------------------------------------------------------
# 6. GET /companies
# ---------------------------------------------------------
@router.get(
    "/companies",
    response_model=List[CompanyListItem],
    summary="Get Active Mock Index Companies",
    description="Retrieves the 15-stock mock index universe with latest risk signal statistics and market data quotes."
)
def get_companies(db: Session = Depends(get_db)):
    universe = MarketDataService.DEFAULT_INDEX_UNIVERSE
    company_list: List[CompanyListItem] = []

    for ticker, info in universe.items():
        # Query aggregate signals from DB
        q = db.query(DBRiskSignal).filter(DBRiskSignal.ticker == ticker)
        count = q.count()
        if count > 0:
            avg_sent = db.query(func.avg(DBRiskSignal.sentiment_score)).filter(DBRiskSignal.ticker == ticker).scalar() or 0.0
            avg_imp = db.query(func.avg(DBRiskSignal.impact_score)).filter(DBRiskSignal.ticker == ticker).scalar() or 5.0
            risk_level = FinancialImpactScorer.determine_risk_level(avg_imp, avg_sent, "Other")
        else:
            avg_sent = 0.0
            avg_imp = 5.0
            risk_level = "LOW"

        # Try to pull latest cached market quote
        quote = market_service.get_stock_quote(ticker)
        price = getattr(quote, "current_price", None) if quote else None
        if price is None and quote and hasattr(quote, "price"):
            price = quote.price
        change_pct = quote.change_pct if quote else 0.0

        company_list.append(
            CompanyListItem(
                ticker=ticker,
                name=info["name"],
                sector=info["sector"],
                market_price=price,
                price_change_pct=change_pct,
                base_weight_pct=round(100.0 / len(universe), 2),
                signal_count=count,
                average_sentiment=round(avg_sent, 4),
                average_impact=round(avg_imp, 1),
                risk_level=risk_level
            )
        )

    return company_list

# ---------------------------------------------------------
# 7. GET /events
# ---------------------------------------------------------
@router.get(
    "/events",
    response_model=List[EventTypeItem],
    summary="Get Controlled Event Taxonomy",
    description="Returns the 10 controlled event taxonomy classes with definitions, severity weights, and signal frequency."
)
def get_events(db: Session = Depends(get_db)):
    items: List[EventTypeItem] = []
    for cat in FinancialEventClassifier.CONTROLLED_TAXONOMY:
        count = db.query(DBRiskSignal).filter(DBRiskSignal.event_type == cat).count()
        items.append(
            EventTypeItem(
                event_type=cat,
                description=EVENT_DESCRIPTIONS.get(cat, "Controlled financial event category."),
                severity_weight=FinancialEventClassifier.SEVERITY_WEIGHTS.get(cat, 0.50),
                signal_count=count
            )
        )
    return items
