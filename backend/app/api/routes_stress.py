import json
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List

from backend.app.database.connection import get_db
from backend.app.database.models import RiskSignal, StressTestRun
from backend.app.schemas.common import APIResponse
from backend.app.schemas.stress_schemas import (
    StressSimulationRequest,
    StressSimulationResult
)
from backend.app.portfolio.portfolio_manager import PortfolioManager
from backend.app.stress_testing.simulator import StressSimulator

router = APIRouter(prefix="/stress-test")
stress_simulator = StressSimulator()

@router.post("/simulate", response_model=APIResponse[StressSimulationResult])
def run_stress_test(
    payload: StressSimulationRequest = Body(...),
    db: Session = Depends(get_db)
):
    portfolio = PortfolioManager.get_default_portfolio()

    # If specific signals are requested or NLP shock scenario selected
    active_signals = []
    if payload.scenario == "NLP_NEWS_SHOCK" or payload.signal_ids:
        query = db.query(RiskSignal)
        if payload.signal_ids:
            query = query.filter(RiskSignal.id.in_(payload.signal_ids))
        else:
            query = query.order_by(RiskSignal.id.desc()).limit(10)
        
        db_signals = query.all()
        active_signals = [
            {
                "ticker": s.ticker,
                "sentiment_score": s.sentiment_score,
                "impact_score": s.impact_score,
                "event_type": s.event_type
            } for s in db_signals
        ]

    # Execute simulation
    result = stress_simulator.run_simulation(
        portfolio=portfolio,
        request=payload,
        active_signals=active_signals
    )

    # Persist audit record in DB
    try:
        run_record = StressTestRun(
            portfolio_id=portfolio.id or "default",
            scenario_type=payload.scenario,
            scenario_name=result.scenario_name,
            base_portfolio_value=result.base_portfolio_value,
            stressed_portfolio_value=result.stressed_portfolio_value,
            pnl_loss_amount=result.pnl_loss_amount,
            pnl_loss_pct=result.pnl_loss_pct,
            pre_var_95=result.pre_var_95,
            post_var_95=result.post_var_95,
            pre_cvar_95=result.pre_cvar_95,
            post_cvar_95=result.post_cvar_95,
            metrics_json=json.dumps([a.model_dump() for a in result.asset_breakdown])
        )
        db.add(run_record)
        db.commit()
    except Exception as e:
        db.rollback()

    return APIResponse(status="success", data=result)
