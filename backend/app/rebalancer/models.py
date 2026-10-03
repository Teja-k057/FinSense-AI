from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RebalanceAction(str, Enum):
    INCREASE = "INCREASE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"

class ConstituentRebalanceDetail(BaseModel):
    """Detailed rebalancing metrics and explainability for a single mock index constituent."""
    ticker: str
    company_name: str
    sector: str
    current_price: float = Field(..., description="Current stock price in USD")
    current_index_weight: float = Field(..., ge=0.0, le=1.0, description="Baseline weight in [0.0, 1.0]")
    current_weight_pct: float = Field(..., ge=0.0, le=100.0, description="Baseline weight in percentage")
    target_weight: float = Field(..., ge=0.0, le=1.0, description="Tactical target weight in [0.0, 1.0]")
    target_weight_pct: float = Field(..., ge=0.0, le=100.0, description="Tactical target weight in percentage")
    weight_delta_pct: float = Field(..., description="Target % minus Current %")
    recent_return: float = Field(0.0, description="Recent return (e.g. 1-month trailing return)")
    volatility: Optional[float] = Field(None, description="Realized annualized volatility")
    latest_sentiment_score: float = Field(0.0, ge=-1.0, le=1.0, description="Aggregated sentiment score [-1.0, +1.0]")
    latest_impact_score: float = Field(5.0, ge=1.0, le=10.0, description="Aggregated impact score [1.0, 10.0]")
    latest_event_type: str = Field("Other", description="Dominant event category from 10-class taxonomy")
    calculated_risk_signal: float = Field(0.0, ge=-1.0, le=1.0, description="Net tactical tilt signal [-1.0, +1.0]")
    rebalance_action: RebalanceAction = Field(..., description="Tactical action: INCREASE, HOLD, REDUCE")
    explanation: str = Field(..., description="Plain-English reasoning explaining the weight adjustment")

class RebalanceSummary(BaseModel):
    """Aggregate summary of index before-and-after rebalancing run."""
    as_of: datetime = Field(default_factory=utc_now)
    universe_size: int = 15
    total_current_weight_pct: float = 100.0
    total_target_weight_pct: float = 100.0
    turnover_pct: float = Field(..., description="Portfolio turnover percentage (Sum |delta| / 2)")
    actions_count: Dict[str, int] = Field(default_factory=dict)
    average_sentiment: float = 0.0
    average_impact: float = 5.0
    top_increased: List[str] = Field(default_factory=list)
    top_reduced: List[str] = Field(default_factory=list)
    constituents: List[ConstituentRebalanceDetail]
    methodology: str = (
        "Tactical High-Frequency Stock Index Rebalancer Prototype "
        "(Academic Hackathon Model - Not Financial or Investment Advice)"
    )

class RebalanceRequest(BaseModel):
    """Configuration options for a rebalance execution."""
    min_weight: float = Field(0.02, ge=0.005, le=0.05, description="Minimum single stock weight (floor: 0.5% - 5%)")
    max_weight: float = Field(0.15, ge=0.10, le=0.30, description="Maximum single stock weight (cap: 10% - 30%)")
    action_threshold: float = Field(0.0025, ge=0.001, le=0.02, description="Deadband threshold for action trigger (e.g. 0.25%)")
    max_turnover: Optional[float] = Field(None, ge=0.01, le=1.0, description="Optional maximum turnover constraint")
    use_live_market_data: bool = Field(True, description="Query yfinance cache/live data for current prices")
