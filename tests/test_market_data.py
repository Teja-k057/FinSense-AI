import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import pandas as pd
import numpy as np

from backend.app.portfolio.market_data import MarketDataService
from backend.app.portfolio.models import TickerMarketData, IndexUniverseSummary

class TestMarketDataService(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.service = MarketDataService(
            cache_dir=self.test_dir,
            cache_ttl_hours=12
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("yfinance.Ticker")
    def test_01_successful_quote_and_metrics(self, mock_ticker_cls):
        """Test quote parsing, returns calculation, and volatility from valid historical data."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        # Synthetic 5-day price series
        dates = pd.date_range("2024-03-10", periods=5, freq="D")
        closes = [180.0, 182.0, 185.0, 183.0, 186.0]
        volumes = [5000000, 6000000, 5500000, 4800000, 5200000]
        df = pd.DataFrame({"Close": closes, "Volume": volumes}, index=dates)
        mock_ticker.history.return_value = df
        mock_ticker.fast_info = MagicMock(market_cap=2.8e12)

        quote = self.service.get_stock_quote("AAPL", force_refresh=True)

        self.assertIsInstance(quote, TickerMarketData)
        self.assertEqual(quote.ticker, "AAPL")
        self.assertTrue(quote.is_available)
        self.assertEqual(quote.status, "LIVE")
        self.assertEqual(quote.current_price, 186.0)
        self.assertEqual(quote.previous_close, 183.0)
        # Expected change: (186 - 183) / 183 * 100 = 1.64%
        self.assertEqual(quote.change_pct, 1.64)
        self.assertEqual(quote.volume, 5200000)
        self.assertGreater(quote.annualized_volatility, 0.0)
        self.assertEqual(len(quote.historical_prices), 5)
        self.assertEqual(len(quote.trailing_daily_returns), 4)
        self.assertIsNotNone(quote.as_of)
        self.assertIsNotNone(quote.retrieved_at)

    @patch("yfinance.Ticker")
    def test_02_missing_or_delisted_ticker(self, mock_ticker_cls):
        """Test missing ticker returns is_available=False without fabricating prices."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        # Return empty DataFrame for missing/delisted symbol
        mock_ticker.history.return_value = pd.DataFrame()

        quote = self.service.get_stock_quote("INVALIDXYZ", force_refresh=True)

        self.assertFalse(quote.is_available)
        self.assertEqual(quote.status, "UNAVAILABLE")
        self.assertIsNone(quote.current_price, "Price must never be fabricated for missing ticker")
        self.assertIn("No market data found", quote.error_message)

    @patch("yfinance.Ticker")
    def test_03_network_or_api_exception(self, mock_ticker_cls):
        """Test yfinance network/API exception is caught and returned gracefully."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        mock_ticker.history.side_effect = Exception("Yahoo Finance API 500 Internal Server Error")

        quote = self.service.get_stock_quote("MSFT", force_refresh=True)

        self.assertFalse(quote.is_available)
        self.assertEqual(quote.status, "UNAVAILABLE")
        self.assertIsNone(quote.current_price)
        self.assertIn("yfinance query failed", quote.error_message)

    @patch("yfinance.Ticker")
    def test_04_cache_reuse_within_ttl(self, mock_ticker_cls):
        """Test quotes are cached locally and reused on subsequent calls without querying yfinance."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        dates = pd.date_range("2024-03-10", periods=3, freq="D")
        df = pd.DataFrame({"Close": [200.0, 202.0, 205.0], "Volume": [1000, 2000, 3000]}, index=dates)
        mock_ticker.history.return_value = df
        mock_ticker.fast_info = MagicMock(market_cap=5e11)

        # First call: hits yfinance
        quote1 = self.service.get_stock_quote("JPM", force_refresh=True)
        self.assertEqual(quote1.status, "LIVE")
        self.assertEqual(mock_ticker.history.call_count, 1)

        # Second call: hits cache
        quote2 = self.service.get_stock_quote("JPM", force_refresh=False)
        self.assertEqual(quote2.status, "CACHED")
        self.assertEqual(quote2.current_price, 205.0)
        self.assertEqual(mock_ticker.history.call_count, 1, "Cached quote must not make repeat API call")

    @patch("yfinance.Ticker")
    def test_05_mock_index_universe_retrieval(self, mock_ticker_cls):
        """Test retrieving all constituents of the 15-stock mock index universe."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        dates = pd.date_range("2024-03-10", periods=3, freq="D")
        df = pd.DataFrame({"Close": [100.0, 102.0, 104.0]}, index=dates)
        mock_ticker.history.return_value = df
        mock_ticker.fast_info = MagicMock(market_cap=1e11)

        summary = self.service.get_index_universe_market_data(force_refresh=True)

        self.assertIsInstance(summary, IndexUniverseSummary)
        self.assertEqual(summary.universe_size, 15)
        self.assertEqual(summary.available_count, 15)
        self.assertEqual(summary.unavailable_count, 0)
        self.assertIn("AAPL", summary.constituents)
        self.assertIn("JPM", summary.constituents)
        self.assertIn("TSLA", summary.constituents)

    @patch("yfinance.Ticker")
    def test_06_covariance_matrix_computation(self, mock_ticker_cls):
        """Test covariance matrix computation on mock index constituents."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        dates = pd.date_range("2024-03-01", periods=10, freq="D")
        df = pd.DataFrame({"Close": np.linspace(100, 110, 10)}, index=dates)
        mock_ticker.history.return_value = df
        mock_ticker.fast_info = MagicMock(market_cap=1e11)

        test_tickers = ["AAPL", "NVDA", "JPM"]
        tickers, cov = self.service.get_covariance_matrix(test_tickers)

        self.assertEqual(tickers, test_tickers)
        self.assertEqual(cov.shape, (3, 3))
        # Diagonal elements must be strictly positive variances
        for i in range(3):
            self.assertGreater(cov[i, i], 0.0)
        # Symmetry check: cov[i, j] == cov[j, i]
        np.testing.assert_allclose(cov, cov.T, rtol=1e-5)

if __name__ == "__main__":
    unittest.main()
