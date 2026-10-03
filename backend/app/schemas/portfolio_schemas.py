from typing import List, Optional
from pydantic import BaseModel, Field

class PositionItem(BaseModel):
    ticker: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Asset weight in portfolio [0, 1]")
    sector: Optional[str] = "General"

class PortfolioConfig(BaseModel):
    id: Optional[str] = "default"
    name: str = "Institutional Core Portfolio"
    total_value: float = Field(10_000_000.0, gt=0, description="Portfolio base capital in USD")
    positions: List[PositionItem]

class AssetMarketStats(BaseModel):
    ticker: str
    last_price: float
    annualized_volatility: float
    beta: float
    sector: str
