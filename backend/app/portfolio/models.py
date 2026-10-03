from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class HistoricalPricePoint(BaseModel):
    """Daily historical price and return record for index rebalancing calculation."""
    date: str
    close: float = Field(..., gt=0.0)
    daily_return: Optional[float] = None
    volume: Optional[int] = None

class TickerMarketData(BaseModel):
    """Complete market data quote and risk metrics for a single stock constituent."""
    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = "General"
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    annualized_volatility: Optional[float] = None
    beta: Optional[float] = None
    trailing_daily_returns: List[float] = Field(default_factory=list)
    historical_prices: List[HistoricalPricePoint] = Field(default_factory=list)
    is_available: bool = True
    status: str = "LIVE"  # LIVE, CACHED, UNAVAILABLE
    error_message: Optional[str] = None
    as_of: datetime = Field(default_factory=utc_now)
    retrieved_at: datetime = Field(default_factory=utc_now)

    @property
    def price(self) -> Optional[float]:
        return self.current_price

class IndexUniverseSummary(BaseModel):
    """Aggregate market data overview for the 10-20 stock mock index universe."""
    universe_size: int
    available_count: int
    unavailable_count: int
    as_of: datetime = Field(default_factory=utc_now)
    constituents: Dict[str, TickerMarketData] = Field(default_factory=dict)
