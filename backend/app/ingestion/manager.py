import logging
from typing import Dict, Any, List, Optional

from backend.app.ingestion.adapters.gdelt_adapter import GDELTNewsAdapter
from backend.app.ingestion.adapters.kaggle_adapter import KaggleNewsAdapter
from backend.app.ingestion.adapters.yfinance_adapter import YFinanceAdapter
from backend.app.ingestion.models import AcquisitionSummary, NewsDocument, MarketDataQuote

logger = logging.getLogger("ingestion.manager")

class DataAcquisitionManager:
    """Centralized orchestrator managing multi-source free data acquisition adapters."""

    def __init__(self):
        self.gdelt_adapter = GDELTNewsAdapter()
        self.kaggle_adapter = KaggleNewsAdapter()
        self.yfinance_adapter = YFinanceAdapter()

    def acquire_gdelt(
        self,
        query: str = GDELTNewsAdapter.DEFAULT_FINANCIAL_QUERY,
        timespan: str = GDELTNewsAdapter.DEFAULT_TIMESPAN,
        max_records: int = 50
    ) -> AcquisitionSummary:
        """Acquires live financial news documents from GDELT 2.0 API with deduplication."""
        return self.gdelt_adapter.fetch_news(
            query=query,
            timespan=timespan,
            max_records=max_records
        )

    def acquire_kaggle(self, limit: int = 50, force_download: bool = False) -> AcquisitionSummary:
        """Automatically downloads, caches, and normalizes public Kaggle financial news."""
        return self.kaggle_adapter.acquire(limit=limit, force_download=force_download)

    def acquire_market_data(self, tickers: Optional[List[str]] = None, force_refresh: bool = False) -> AcquisitionSummary:
        """Acquires real-time/cached market prices and stats for index constituents via yfinance."""
        return self.yfinance_adapter.acquire(tickers=tickers, force_refresh=force_refresh)

    def acquire_all_sources(self) -> Dict[str, AcquisitionSummary]:
        """Runs full acquisition across all three free resources."""
        return {
            "gdelt": self.acquire_gdelt(),
            "kaggle": self.acquire_kaggle(),
            "yfinance": self.acquire_market_data()
        }

    def get_source_health(self) -> Dict[str, Dict[str, Any]]:
        """Returns metadata status and health check across all registered adapters."""
        return {
            "gdelt": {
                "adapter": "GDELTNewsAdapter",
                "api_endpoint": self.gdelt_adapter.api_base,
                "seen_articles_count": len(self.gdelt_adapter.seen_article_ids),
                "requires_credentials": False
            },
            "kaggle": {
                "adapter": "KaggleNewsAdapter",
                "public_url": self.kaggle_adapter.public_url,
                "cached": self.kaggle_adapter.cache_file.exists(),
                "requires_credentials": False
            },
            "yfinance": {
                "adapter": "YFinanceAdapter",
                "index_universe_size": len(self.yfinance_adapter.DEFAULT_INDEX_UNIVERSE),
                "cached": self.yfinance_adapter.cache_file.exists(),
                "requires_credentials": False
            }
        }
