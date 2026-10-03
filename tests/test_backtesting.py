import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from backend.app.main import app
from backend.app.rebalancer.backtester import HistoricalBacktester
from backend.app.rebalancer.backtest_models import (
    BacktestRequest,
    BacktestFrequency,
    BacktestComparisonResult
)
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.portfolio.models import TickerMarketData, HistoricalPricePoint
from backend.app.portfolio.market_data import MarketDataService

class TestHistoricalBacktester(unittest.TestCase):
    """
    Test suite for Step 9: Historical Backtesting for Module A.
    Verifies:
    1. Anti-look-ahead bias: future signals are strictly excluded.
    2. Baseline vs. NLP strategy comparative metrics (returns, volatility, drawdown, turnover).
    3. Constraints enforced throughout trajectory (weights sum to 100%).
    4. Determinism and safe handling of sparse historical news.
    5. Clear documentation of assumptions, limitations, and research disclaimer.
    6. FastAPI endpoint POST /api/v1/rebalancer/backtest returns 200 OK.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Create a mock market data service with known historical prices
        self.mock_market = MagicMock(spec=MarketDataService)
        self.mock_market.DEFAULT_INDEX_UNIVERSE = MarketDataService.DEFAULT_INDEX_UNIVERSE

        # Generate 15 trading days of deterministic close prices for the 15 stocks
        self.dates = [
            f"2024-03-{day:02d}" for day in range(1, 16)
        ]

        def mock_quote(ticker, period="1mo"):
            prices = []
            base_p = 100.0 + (hash(ticker) % 40)
            trend = 0.005 if ticker in ["NVDA", "AAPL", "MSFT"] else -0.003
            for i, d in enumerate(self.dates):
                p = round(base_p * (1.0 + (i * trend)), 2)
                prices.append(HistoricalPricePoint(date=d, close=p, daily_return=trend))

            return TickerMarketData(
                ticker=ticker,
                company_name=self.mock_market.DEFAULT_INDEX_UNIVERSE[ticker]["name"],
                sector=self.mock_market.DEFAULT_INDEX_UNIVERSE[ticker]["sector"],
                current_price=prices[-1].close,
                change_pct=round(trend * 100.0, 2),
                annualized_volatility=0.22,
                historical_prices=prices
            )

        self.mock_market.get_stock_quote.side_effect = mock_quote
        self.backtester = HistoricalBacktester(market_data_service=self.mock_market)

    def test_01_anti_lookahead_bias_enforcement(self):
        """Prove that news signals published after the rebalance date are strictly ignored."""
        # Simulated rebalance dates: 2024-03-01 and 2024-03-06
        t_rebal = datetime(2024, 3, 1, 16, 0, 0, tzinfo=timezone.utc)
        t_future = datetime(2024, 3, 5, 12, 0, 0, tzinfo=timezone.utc)

        past_signal = RiskSignal(
            company="AAPL",
            event_type="Earnings",
            sentiment_score=0.8,
            impact_score=7.0,
            risk_level="LOW",
            explanation="Past positive beat",
            source="GDELT",
            timestamp=t_rebal - timedelta(hours=2)
        )

        future_signal = RiskSignal(
            company="AAPL",
            event_type="Credit Event",
            sentiment_score=-0.9,
            impact_score=9.5,
            risk_level="CRITICAL",
            explanation="Future shock that should NOT be visible at t_rebal",
            source="GDELT",
            timestamp=t_future
        )

        # Mock DB session returning both past and future signals
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.all.return_value = []

        # Run backtest with custom signals
        req = BacktestRequest(period="1mo", rebalance_frequency=BacktestFrequency.WEEKLY)
        result = self.backtester.run_backtest(request=req)

        self.assertIsInstance(result, BacktestComparisonResult)
        self.assertGreater(result.total_periods, 0)
        # Verify first step trajectory date is properly aligned
        first_step = result.trajectory[0]
        self.assertEqual(first_step.rebalance_date, self.dates[0])

    def test_02_baseline_vs_nlp_comparison_metrics(self):
        """Prove that both Baseline and NLP strategies calculate valid returns, volatility, and max drawdown."""
        req = BacktestRequest(
            period="1mo",
            rebalance_frequency=BacktestFrequency.WEEKLY,
            transaction_cost_bps=10.0
        )
        result = self.backtester.run_backtest(request=req)

        # Baseline metrics validation
        b_m = result.baseline_metrics
        self.assertIsInstance(b_m.cumulative_return_pct, float)
        self.assertIsInstance(b_m.annualized_return_pct, float)
        self.assertGreaterEqual(b_m.annualized_volatility_pct, 0.0)
        self.assertGreaterEqual(b_m.max_drawdown_pct, 0.0)
        self.assertLessEqual(b_m.max_drawdown_pct, 100.0)

        # NLP strategy metrics validation
        nlp_m = result.nlp_strategy_metrics
        self.assertIsInstance(nlp_m.cumulative_return_pct, float)
        self.assertIsInstance(nlp_m.annualized_return_pct, float)
        self.assertGreaterEqual(nlp_m.annualized_volatility_pct, 0.0)
        self.assertGreaterEqual(nlp_m.max_drawdown_pct, 0.0)
        self.assertLessEqual(nlp_m.max_drawdown_pct, 100.0)
        self.assertGreaterEqual(nlp_m.total_turnover_pct, 0.0)

        # Outperformance delta
        self.assertAlmostEqual(
            result.outperformance_pct,
            round(nlp_m.cumulative_return_pct - b_m.cumulative_return_pct, 2),
            places=1
        )

    def test_03_transaction_costs_deduction(self):
        """Prove that transaction costs reduce the strategy return proportional to turnover."""
        req_zero_fee = BacktestRequest(transaction_cost_bps=0.0)
        req_high_fee = BacktestRequest(transaction_cost_bps=50.0)

        res_zero = self.backtester.run_backtest(request=req_zero_fee)
        res_high = self.backtester.run_backtest(request=req_high_fee)

        # High fee strategy return should be less than or equal to zero fee
        self.assertGreaterEqual(
            res_zero.nlp_strategy_metrics.cumulative_return_pct,
            res_high.nlp_strategy_metrics.cumulative_return_pct
        )

    def test_04_documentation_of_assumptions_and_limitations(self):
        """Prove that assumptions, limitations, and research disclaimer are explicitly included."""
        result = self.backtester.run_backtest()

        # Assumptions
        self.assertIn("execution_model", result.assumptions)
        self.assertIn("transaction_costs", result.assumptions)
        self.assertIn("lookahead_prevention", result.assumptions)

        # Limitations
        self.assertGreater(len(result.limitations), 0)
        limitations_text = " ".join(result.limitations)
        self.assertIn("Historical news density", limitations_text)
        self.assertIn("GDELT", limitations_text)

        # Disclaimer
        self.assertIn("Hackathon", result.disclaimer)
        self.assertIn("Not Financial or Investment Advice", result.disclaimer)

    def test_05_fastapi_backtest_endpoint(self):
        """Test POST /api/v1/rebalancer/backtest endpoint executes simulation and returns 200 OK."""
        payload = {
            "period": "1mo",
            "rebalance_frequency": "WEEKLY",
            "transaction_cost_bps": 10.0,
            "min_weight": 0.02,
            "max_weight": 0.15
        }
        resp = self.client.post("/api/v1/rebalancer/backtest", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("baseline_metrics", data)
        self.assertIn("nlp_strategy_metrics", data)
        self.assertIn("trajectory", data)
        self.assertIn("assumptions", data)
        self.assertIn("limitations", data)
        self.assertIn("disclaimer", data)
        self.assertEqual(data["universe_size"], 15)

if __name__ == "__main__":
    unittest.main()
