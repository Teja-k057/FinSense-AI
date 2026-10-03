import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models import RiskSignal as DBRiskSignal
from backend.app.rebalancer.models import (
    RebalanceSummary,
    RebalanceRequest,
    ConstituentRebalanceDetail
)
from backend.app.rebalancer.backtest_models import (
    BacktestRequest,
    BacktestComparisonResult
)
from backend.app.rebalancer.rebalancing_engine import RebalancingEngine
from backend.app.rebalancer.backtester import HistoricalBacktester
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.api.routes_risk import _map_db_to_signal

logger = logging.getLogger("api.routes_rebalancer")

router = APIRouter(prefix="/rebalancer", tags=["Module A: Stock Index Rebalancer"])
rebalancing_engine = RebalancingEngine()

# Cache latest rebalance run in memory
_LATEST_REBALANCE_CACHE: Optional[RebalanceSummary] = None

@router.get(
    "/index",
    summary="Get Mock Index Universe",
    description="Retrieves the 15-stock mock index universe with baseline equal weights and current market quotes."
)
def get_mock_index():
    return {
        "universe_name": "S&P Global x CRISIL 15-Stock Tactical Index",
        "universe_size": len(RebalancingEngine.DEFAULT_UNIVERSE),
        "benchmark_weighting": "Equal-Weighted (6.67% baseline)",
        "sectors": ["Technology", "Financials", "Energy", "Healthcare", "Consumer Discretionary"],
        "constituents": RebalancingEngine.DEFAULT_UNIVERSE
    }

@router.post(
    "/rebalance",
    response_model=RebalanceSummary,
    summary="Execute Tactical Index Rebalancing",
    description=(
        "Executes Module A Tactical High-Frequency Stock Index Rebalancing. "
        "Aggregates recent NLP Risk Engine signals from the database and yfinance market movements "
        "to calculate constrained target weights with full explainability."
    )
)
def execute_rebalance(
    request: Optional[RebalanceRequest] = None,
    db: Session = Depends(get_db)
):
    global _LATEST_REBALANCE_CACHE
    req = request or RebalanceRequest()

    try:
        # 1. Fetch recent signals from DB grouped by ticker
        db_signals = db.query(DBRiskSignal).order_by(DBRiskSignal.created_at.desc()).limit(200).all()
        signals_by_ticker: Dict[str, List[RiskSignal]] = {}

        for r in db_signals:
            ticker = r.ticker.upper().strip()
            sig = _map_db_to_signal(r, db)
            if ticker not in signals_by_ticker:
                signals_by_ticker[ticker] = []
            signals_by_ticker[ticker].append(sig)

        # 2. Run RebalancingEngine
        summary = rebalancing_engine.rebalance(
            signals_by_ticker=signals_by_ticker,
            config=req
        )

        _LATEST_REBALANCE_CACHE = summary
        return summary

    except Exception as e:
        logger.error(f"[Rebalancer] Rebalancing execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rebalance execution failed: {str(e)}"
        )

@router.get(
    "/latest",
    response_model=RebalanceSummary,
    summary="Get Latest Rebalance Result",
    description="Retrieves the most recent rebalancing run from cache, or executes a new run if none exists."
)
def get_latest_rebalance(db: Session = Depends(get_db)):
    global _LATEST_REBALANCE_CACHE
    if _LATEST_REBALANCE_CACHE is not None:
        return _LATEST_REBALANCE_CACHE
    return execute_rebalance(request=None, db=db)

@router.post(
    "/backtest",
    response_model=BacktestComparisonResult,
    summary="Run Historical Backtest (Baseline vs NLP Rebalancer)",
    description=(
        "Simulates historical performance comparing an Equal-Weight Baseline Index "
        "versus the NLP Risk Engine Tactical Rebalancer. Strictly enforces anti-look-ahead bias."
    )
)
def run_historical_backtest(
    request: Optional[BacktestRequest] = None,
    db: Session = Depends(get_db)
):
    try:
        backtester = HistoricalBacktester(
            market_data_service=rebalancing_engine.market_service,
            rebalancing_engine=rebalancing_engine
        )
        result = backtester.run_backtest(request=request, db=db)
        return result
    except Exception as e:
        logger.error(f"[Backtester] Historical backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest execution failed: {str(e)}"
        )
