from typing import Dict, Any, List
from backend.app.schemas.portfolio_schemas import PortfolioConfig, PositionItem

class PortfolioManager:
    """Manages baseline and custom portfolio configurations."""

    @staticmethod
    def get_default_portfolio() -> PortfolioConfig:
        return PortfolioConfig(
            id="default",
            name="S&P Institutional Multi-Asset Portfolio",
            total_value=10_000_000.0,
            positions=[
                PositionItem(ticker="JPM", weight=0.25, sector="Financials"),
                PositionItem(ticker="AAPL", weight=0.25, sector="Technology"),
                PositionItem(ticker="NVDA", weight=0.20, sector="Technology"),
                PositionItem(ticker="XOM", weight=0.15, sector="Energy"),
                PositionItem(ticker="JNJ", weight=0.15, sector="Healthcare"),
            ]
        )
