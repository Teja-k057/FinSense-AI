import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
import yfinance as yf

from backend.app.config.settings import settings
from backend.app.ingestion.adapters.base import BaseAdapter
from backend.app.ingestion.models import MarketDataQuote, AcquisitionSummary

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class YFinanceAdapter(BaseAdapter):
    """Adapter for automated market data acquisition via yfinance."""

    # Curated 15-stock mock index constituents across 5 sectors
    DEFAULT_INDEX_UNIVERSE = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",  # Tech / Growth
        "JPM", "BAC", "GS",                       # Financials
        "XOM", "CVX",                             # Energy
        "JNJ", "PFE", "UNH",                      # Healthcare
        "TSLA", "BA"                              # Consumer / Industrials
    ]

    FALLBACK_BENCHMARKS = {
        "AAPL": {"price": 225.50, "vol": 0.22, "beta": 1.10, "cap": 3.4e12},
        "MSFT": {"price": 420.00, "vol": 0.20, "beta": 1.05, "cap": 3.1e12},
        "NVDA": {"price": 125.00, "vol": 0.45, "beta": 1.85, "cap": 3.0e12},
        "GOOGL": {"price": 165.00, "vol": 0.24, "beta": 1.15, "cap": 2.0e12},
        "AMZN": {"price": 185.00, "vol": 0.28, "beta": 1.20, "cap": 1.9e12},
        "JPM": {"price": 210.00, "vol": 0.21, "beta": 1.12, "cap": 6.0e11},
        "BAC": {"price": 39.50, "vol": 0.26, "beta": 1.25, "cap": 3.1e11},
        "GS": {"price": 480.00, "vol": 0.25, "beta": 1.30, "cap": 1.6e11},
        "XOM": {"price": 118.00, "vol": 0.22, "beta": 0.85, "cap": 4.7e11},
        "CVX": {"price": 150.00, "vol": 0.21, "beta": 0.88, "cap": 2.8e11},
        "JNJ": {"price": 160.00, "vol": 0.14, "beta": 0.55, "cap": 3.8e11},
        "PFE": {"price": 28.50, "vol": 0.23, "beta": 0.65, "cap": 1.6e11},
        "UNH": {"price": 570.00, "vol": 0.18, "beta": 0.72, "cap": 5.2e11},
        "TSLA": {"price": 240.00, "vol": 0.52, "beta": 1.90, "cap": 7.6e11},
        "BA": {"price": 155.00, "vol": 0.38, "beta": 1.45, "cap": 9.5e10}
    }

    def __init__(self):
        super().__init__("yfinance")
        self.cache_dir = settings.MARKET_CACHE_DIR
        self.cache_file = self.cache_dir / "market_quotes_cache.json"
        self.cache_ttl_hours = settings.YFINANCE_CACHE_TTL_HOURS

    def acquire(
        self,
        tickers: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> AcquisitionSummary:
        return self.execute_with_timing(
            self._acquire_internal,
            tickers=tickers or self.DEFAULT_INDEX_UNIVERSE,
            force_refresh=force_refresh
        )

    def _acquire_internal(self, tickers: List[str], force_refresh: bool) -> AcquisitionSummary:
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            try:
                cached = self._read_cache()
                if cached and all(t in cached for t in tickers):
                    quotes = [MarketDataQuote(**cached[t]) for t in tickers if t in cached]
                    self.logger.info(f"Reusing cached market data for {len(quotes)} tickers.")
                    return AcquisitionSummary(
                        source=self.source_name,
                        record_count=len(quotes),
                        status="SUCCESS_CACHED",
                        is_fallback=False,
                        duration_ms=0.0,
                        records=quotes
                    )
            except Exception as e:
                self.logger.warning(f"Failed loading market cache: {e}")

        quotes: List[MarketDataQuote] = []
        cache_dict: Dict[str, dict] = {}
        has_any_live = False

        for ticker in tickers:
            ticker_clean = ticker.upper().strip()
            quote = None

            # 1. Attempt yfinance query
            try:
                t = yf.Ticker(ticker_clean)
                fast_info = getattr(t, "fast_info", None)
                price = getattr(fast_info, "last_price", None) or getattr(fast_info, "previous_close", None)
                
                if price and float(price) > 0:
                    fb = self.FALLBACK_BENCHMARKS.get(ticker_clean, {"vol": 0.25, "beta": 1.0, "cap": 1e11})
                    mcap = getattr(fast_info, "market_cap", None) or fb["cap"]
                    
                    quote = MarketDataQuote(
                        ticker=ticker_clean,
                        price=round(float(price), 2),
                        change_pct=0.0,
                        market_cap=float(mcap) if mcap else None,
                        volatility_annual=fb["vol"],
                        beta=fb["beta"],
                        is_fallback=False,
                        status="LIVE",
                        acquired_at=utc_now()
                    )
                    has_any_live = True
            except Exception as e:
                self.logger.debug(f"Live yfinance query for {ticker_clean} failed: {e}")

            # 2. Transparent Fallback if yfinance failed for this individual ticker
            if not quote:
                fb = self.FALLBACK_BENCHMARKS.get(ticker_clean, {"price": 100.0, "vol": 0.25, "beta": 1.0, "cap": 1e11})
                quote = MarketDataQuote(
                    ticker=ticker_clean,
                    price=fb["price"],
                    change_pct=0.0,
                    market_cap=fb["cap"],
                    volatility_annual=fb["vol"],
                    beta=fb["beta"],
                    is_fallback=True,
                    status="DEMO/FALLBACK",
                    acquired_at=utc_now()
                )

            quotes.append(quote)
            cache_dict[ticker_clean] = quote.model_dump(mode="json")

        # Save cache
        self._write_cache(cache_dict)

        overall_status = "SUCCESS_LIVE" if has_any_live else "DEMO/FALLBACK"
        return AcquisitionSummary(
            source=self.source_name,
            record_count=len(quotes),
            status=overall_status,
            is_fallback=not has_any_live,
            duration_ms=0.0,
            records=quotes
        )

    def _is_cache_valid(self) -> bool:
        if not self.cache_file.exists():
            return False
        mtime = self.cache_file.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600.0
        return age_hours < self.cache_ttl_hours

    def _read_cache(self) -> dict:
        with open(self.cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_cache(self, data: dict):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Error caching market quotes: {e}")
