from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class BacktestFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

class BacktestRequest(BaseModel):
    """Configuration options for historical backtesting simulation."""
    period: str = Field("1mo", description="Historical duration: 1mo, 3mo, 6mo")
    rebalance_frequency: BacktestFrequency = Field(BacktestFrequency.WEEKLY, description="Rebalance interval: DAILY, WEEKLY, MONTHLY")
    transaction_cost_bps: float = Field(10.0, ge=0.0, le=100.0, description="Transaction fee in basis points per 100% turnover (e.g. 10 bps = 0.10%)")
    min_weight: float = Field(0.02, ge=0.005, le=0.05, description="Constituent weight floor (e.g. 2%)")
    max_weight: float = Field(0.15, ge=0.10, le=0.30, description="Constituent weight cap (e.g. 15%)")
    action_threshold: float = Field(0.0025, description="Deadband threshold for action trigger (0.25%)")

class PeriodBacktestPoint(BaseModel):
    """Single period step in the backtest trajectory."""
    period_index: int
    date: str
    rebalance_date: str
    subsequent_date: str
    baseline_period_return_pct: float
    nlp_period_return_pct: float
    active_period_return_pct: float     # nlp - baseline
    baseline_cumulative_return_pct: float
    nlp_cumulative_return_pct: float
    turnover_pct: float
    transaction_cost_pct: float
    top_overweight: List[str] = []      # Tickers with highest positive tilt
    top_underweight: List[str] = []     # Tickers with highest negative tilt
    news_signals_used: int = 0          # Number of point-in-time news signals available at this step

class StrategyPerformanceMetrics(BaseModel):
    """Aggregate financial metrics evaluated over the entire backtesting horizon."""
    cumulative_return_pct: float
    annualized_return_pct: float
    annualized_volatility_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_turnover_pct: float
    win_rate_pct: float                 # Percentage of periods where strategy outperformed baseline

class BacktestComparisonResult(BaseModel):
    """Complete comparative backtest output comparing Baseline Index vs NLP-Rebalanced Index."""
    as_of: datetime = Field(default_factory=utc_now)
    start_date: str
    end_date: str
    rebalance_frequency: str
    total_periods: int
    universe_size: int = 15
    baseline_metrics: StrategyPerformanceMetrics
    nlp_strategy_metrics: StrategyPerformanceMetrics
    outperformance_pct: float           # NLP cumulative % minus Baseline cumulative %
    trajectory: List[PeriodBacktestPoint]
    assumptions: Dict[str, Any]
    limitations: List[str]
    disclaimer: str
