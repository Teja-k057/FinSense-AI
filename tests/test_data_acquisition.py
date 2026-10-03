import unittest
from pathlib import Path

from backend.app.ingestion.adapters.gdelt_adapter import GDELTNewsAdapter
from backend.app.ingestion.adapters.kaggle_adapter import KaggleNewsAdapter
from backend.app.ingestion.adapters.yfinance_adapter import YFinanceAdapter
from backend.app.ingestion.manager import DataAcquisitionManager
from backend.app.ingestion.models import NewsDocument, MarketDataQuote, AcquisitionSummary

class TestDataAcquisitionAdapters(unittest.TestCase):

    def test_01_gdelt_adapter(self):
        """Test GDELT adapter: live fetch if reachable, or clean error capture without data fabrication."""
        adapter = GDELTNewsAdapter(timeout_seconds=3, max_retries=1)
        summary = adapter.fetch_news(query="stocks OR banking", max_records=5)

        self.assertIsInstance(summary, AcquisitionSummary)
        self.assertEqual(summary.source, "GDELT")
        self.assertIn(summary.status, ["SUCCESS_LIVE", "SUCCESS_CACHED", "EMPTY", "ERROR"])

        if summary.status in ["SUCCESS_LIVE", "SUCCESS_CACHED"]:
            self.assertGreater(summary.record_count, 0)
            for record in summary.records:
                self.assertIsInstance(record, NewsDocument)
                self.assertEqual(record.source, "GDELT")
                self.assertGreater(len(record.title), 3)
                self.assertIsNotNone(record.id)
        else:
            # When endpoint times out or errors, never fabricate records
            self.assertEqual(summary.record_count, 0)
            self.assertEqual(len(summary.records), 0)
            self.assertIsNotNone(summary.error_message)

    def test_02_kaggle_adapter_auto_download_and_cache(self):
        """Test automated public download and local caching for Kaggle Financial News."""
        adapter = KaggleNewsAdapter()
        summary = adapter.acquire(limit=10)

        self.assertIsInstance(summary, AcquisitionSummary)
        self.assertEqual(summary.source, "Kaggle")
        self.assertGreater(summary.record_count, 0)

        for record in summary.records:
            self.assertEqual(record.source, "Kaggle")
            self.assertGreater(len(record.title), 3)

    def test_03_yfinance_adapter(self):
        """Test market data retrieval for mock index constituents."""
        adapter = YFinanceAdapter()
        test_universe = ["AAPL", "JPM", "NVDA"]
        summary = adapter.acquire(tickers=test_universe)

        self.assertIsInstance(summary, AcquisitionSummary)
        self.assertEqual(summary.source, "yfinance")
        self.assertEqual(summary.record_count, len(test_universe))

        for quote in summary.records:
            self.assertIsInstance(quote, MarketDataQuote)
            self.assertIn(quote.ticker, test_universe)
            self.assertGreater(quote.price, 0.0)
            self.assertGreater(quote.volatility_annual, 0.0)
            self.assertGreater(quote.beta, 0.0)

    def test_04_data_acquisition_manager(self):
        """Test centralized manager coordination and health metadata."""
        manager = DataAcquisitionManager()
        health = manager.get_source_health()

        self.assertIn("gdelt", health)
        self.assertIn("kaggle", health)
        self.assertIn("yfinance", health)

        # Verify no credentials are required for any adapter
        for src, meta in health.items():
            self.assertFalse(meta["requires_credentials"], f"{src} should not require credentials")

if __name__ == "__main__":
    unittest.main()
