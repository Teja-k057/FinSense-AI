from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional

from backend.app.schemas.common import APIResponse
from backend.app.portfolio.market_data import MarketDataService
from backend.app.portfolio.models import TickerMarketData, IndexUniverseSummary
from backend.app.portfolio.portfolio_manager import PortfolioManager

router = APIRouter(prefix="/portfolio")
market_service = MarketDataService()

@router.get("/default")
def get_default_portfolio():
    """Returns baseline institutional multi-asset portfolio configuration."""
    portfolio = PortfolioManager.get_default_portfolio()
    return APIResponse(status="success", data=portfolio)

@router.get("/quote/{ticker}", response_model=APIResponse[TickerMarketData])
def get_stock_quote(
    ticker: str,
    period: str = Query("1mo", description="Historical period: 5d, 1mo, 3mo, 1y"),
    force_refresh: bool = Query(False)
):
    """
    Retrieves real-time/recent market price, daily returns, and realized volatility
    for a specific constituent via yfinance. Never fabricates prices.
    """
    quote = market_service.get_stock_quote(ticker=ticker, period=period, force_refresh=force_refresh)
    return APIResponse(status="success", data=quote)

@router.get("/index-universe", response_model=APIResponse[IndexUniverseSummary])
def get_index_universe_data(
    force_refresh: bool = Query(False)
):
    """
    Retrieves complete market quotes and volatility for the 15-stock mock index universe.
    Used downstream by the Module A Tactical Stock Index Rebalancer.
    """
    universe = market_service.get_index_universe_market_data(force_refresh=force_refresh)
    return APIResponse(status="success", data=universe)
