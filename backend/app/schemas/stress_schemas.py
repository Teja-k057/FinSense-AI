from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class StressSimulationRequest(BaseModel):
    portfolio_id: str = "default"
    scenario: str = Field("HISTORICAL_2008", description="HISTORICAL_2008, COVID_2020, SVB_2023, NLP_NEWS_SHOCK, CUSTOM")
    confidence_level: float = Field(0.95, ge=0.90, le=0.999)
    signal_ids: Optional[List[int]] = Field(default_factory=list, description="IDs of NLP signals to shock")
    custom_shocks: Optional[Dict[str, float]] = Field(default_factory=dict, description="e.g. {'AAPL': -0.10, 'JPM': -0.15}")
    factor_rate_shock_bps: Optional[float] = Field(0.0, description="Interest rate shift in bps, e.g. +150")

class AssetImpactDetail(BaseModel):
    ticker: str
    sector: str
    weight: float
    base_allocation: float
    shock_pct: float
    pnl_impact: float
    stressed_allocation: float

class StressSimulationResult(BaseModel):
    scenario_name: str
    base_portfolio_value: float
    stressed_portfolio_value: float
    pnl_loss_amount: float
    pnl_loss_pct: float
    pre_var_95: float
    post_var_95: float
    pre_cvar_95: float
    post_cvar_95: float
    asset_breakdown: List[AssetImpactDetail]
    recommendations: List[str]
