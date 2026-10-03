from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database.connection import get_db
from backend.app.database.models import RiskSignal
from backend.app.schemas.common import APIResponse
from backend.app.schemas.nlp_schemas import TextAnalysisRequest, RiskSignalResponse
from backend.app.risk_engine.signals import RiskSignalEngine

router = APIRouter(prefix="/nlp")
signal_engine = RiskSignalEngine()

@router.post("/analyze", response_model=APIResponse[RiskSignalResponse])
def analyze_text(
    payload: TextAnalysisRequest,
    db: Session = Depends(get_db)
):
    signal = signal_engine.process_text(
        raw_text=payload.text,
        source=payload.source or "AdHoc",
        ticker_hint=payload.ticker_hint,
        db=db
    )
    return APIResponse(status="success", data=RiskSignalResponse(**signal.model_dump()))

@router.get("/signals", response_model=APIResponse[List[RiskSignalResponse]])
def get_signals(
    ticker: Optional[str] = Query(None, description="Filter by stock ticker"),
    event_type: Optional[str] = Query(None, description="Filter by event category"),
    min_impact: Optional[float] = Query(1.0, ge=1.0, le=10.0, description="Minimum impact score"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(RiskSignal).filter(RiskSignal.impact_score >= min_impact)
    if ticker:
        query = query.filter(RiskSignal.ticker == ticker.upper())
    if event_type:
        query = query.filter(RiskSignal.event_type == event_type)

    signals = query.order_by(RiskSignal.id.desc()).limit(limit).all()

    resp_data = [
        RiskSignalResponse(
            id=s.id,
            article_id=s.article_id,
            ticker=s.ticker,
            company_name=s.company_name or s.ticker,
            sentiment_score=s.sentiment_score,
            sentiment_label=s.sentiment_label,
            event_type=s.event_type,
            event_confidence=s.event_confidence,
            impact_score=s.impact_score,
            summary=s.summary,
            created_at=s.created_at
        ) for s in signals
    ]
    return APIResponse(status="success", data=resp_data)
