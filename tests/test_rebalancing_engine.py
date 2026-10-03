import unittest
from datetime import datetime
from backend.app.rebalancer.rebalancing_engine import RebalancingEngine
from backend.app.rebalancer.models import (
    RebalanceAction,
    RebalanceRequest,
    ConstituentRebalanceDetail
)
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.portfolio.models import TickerMarketData

class TestRebalancingEngine(unittest.TestCase):
    """
    Unit test suite validating Module A: Tactical Stock Index Rebalancer.
    Verifies:
    1. Target weights strictly sum to 100.0% (1.000000)
    2. Minimum and maximum weight constraints are strictly respected
    3. Strongly negative signals decrease target weight below baseline (REDUCE)
    4. Strongly positive signals increase target weight above baseline (INCREASE)
    5. Neutral/unchanged signals result in HOLD
    6. Missing signals are handled safely without exceptions
    7. No random behavior exists (bitwise determinism across repeated executions)
    8. Turnover limits clamp portfolio rebalancing
    """

    def setUp(self):
        self.engine = RebalancingEngine()

    def test_01_weights_sum_to_100_percent(self):
        """Prove that constrained target weights strictly sum to 1.0 (100.0%) across arbitrary raw signals."""
        raw_scenarios = [
            {"AAPL": 0.9, "MSFT": -0.8, "NVDA": 0.7, "JPM": -0.9, "XOM": 0.0},
            {"AAPL": 1.0, "MSFT": 1.0, "NVDA": 1.0, "JPM": 1.0, "XOM": 1.0},
            {"AAPL": -1.0, "MSFT": -1.0, "NVDA": -1.0, "JPM": -1.0, "XOM": -1.0},
            {"AAPL": 0.05, "MSFT": -0.02, "NVDA": 0.01, "JPM": 0.0, "XOM": -0.01},
        ]

        base_weights = {k: 0.20 for k in ["AAPL", "MSFT", "NVDA", "JPM", "XOM"]}

        for sig_dict in raw_scenarios:
            raw_targets = self.engine.calculate_target_weights(base_weights, sig_dict)
            constrained = self.engine.apply_constraints(raw_targets, min_weight=0.05, max_weight=0.35)

            total_weight = sum(constrained.values())
            self.assertAlmostEqual(total_weight, 1.0, places=5, msg=f"Weights do not sum to 1.0: {total_weight}")

    def test_02_minimum_and_maximum_weight_constraints(self):
        """Prove that no constituent violates the configurable min_weight floor or max_weight cap."""
        # Extreme skewed signals trying to push weights to 0% and 100%
        extreme_signals = {
            "AAPL": 1.0, "MSFT": 1.0, "NVDA": 1.0,
            "GOOGL": -1.0, "AMZN": -1.0, "JPM": -1.0, "BAC": -1.0, "GS": -1.0,
            "XOM": -1.0, "CVX": -1.0, "JNJ": -1.0, "PFE": -1.0, "UNH": -1.0,
            "TSLA": -1.0, "BA": -1.0
        }

        base_weights = {t: 1.0 / 15 for t in extreme_signals}
        min_w = 0.02  # 2.0% floor
        max_w = 0.12  # 12.0% cap

        raw_targets = self.engine.calculate_target_weights(base_weights, extreme_signals, tilt_multiplier=1.0)
        constrained = self.engine.apply_constraints(raw_targets, min_weight=min_w, max_weight=max_w)

        for ticker, w in constrained.items():
            self.assertGreaterEqual(
                w, min_w - 1e-6,
                f"Ticker {ticker} weight {w} breached floor {min_w}"
            )
            self.assertLessEqual(
                w, max_w + 1e-6,
                f"Ticker {ticker} weight {w} breached cap {max_w}"
            )

        self.assertAlmostEqual(sum(constrained.values()), 1.0, places=5)

    def test_03_negative_signals_reduce_weight(self):
        """Prove that negative risk/sentiment signals reliably reduce stock allocation."""
        ticker = "JPM"
        base_w = 1.0 / 15  # ~6.67%

        # Create strongly negative credit event signals
        bad_signals = [
            RiskSignal(
                company="JPM",
                event_type="Credit Event",
                sentiment_score=-0.85,
                impact_score=9.2,
                risk_level="CRITICAL",
                explanation="Massive loan default crisis",
                source="GDELT"
            ),
            RiskSignal(
                company="JPM",
                event_type="Regulatory",
                sentiment_score=-0.75,
                impact_score=8.5,
                risk_level="HIGH",
                explanation="Severe antitrust penalty fine",
                source="GDELT"
            )
        ]

        market_data = TickerMarketData(ticker="JPM", change_pct=-3.5, current_price=190.0)

        sig_result = self.engine.calculate_signal(ticker, bad_signals, market_data)
        self.assertLess(sig_result["tactical_signal"], -0.40)

        signals_map = {t: 0.0 for t in self.engine.DEFAULT_UNIVERSE}
        signals_map["JPM"] = sig_result["tactical_signal"]

        base_weights = {t: base_w for t in self.engine.DEFAULT_UNIVERSE}
        raw_targets = self.engine.calculate_target_weights(base_weights, signals_map)
        constrained = self.engine.apply_constraints(raw_targets, min_weight=0.02, max_weight=0.15)
        actions = self.engine.generate_actions(base_weights, constrained)

        self.assertLess(constrained["JPM"], base_w)
        self.assertEqual(actions["JPM"], RebalanceAction.REDUCE)

        explanation = self.engine.generate_explanations(
            "JPM", base_w, constrained["JPM"], sig_result, actions["JPM"]
        )
        self.assertIn("Weight reduced", explanation)
        self.assertIn("Credit Event", explanation)

    def test_04_positive_signals_increase_weight(self):
        """Prove that positive earnings and growth signals reliably increase stock allocation."""
        ticker = "NVDA"
        base_w = 1.0 / 15  # ~6.67%

        good_signals = [
            RiskSignal(
                company="NVDA",
                event_type="Earnings",
                sentiment_score=0.90,
                impact_score=8.0,
                risk_level="LOW",
                explanation="Record data center revenue beats all estimates",
                source="GDELT"
            ),
            RiskSignal(
                company="NVDA",
                event_type="Product Launch",
                sentiment_score=0.80,
                impact_score=7.0,
                risk_level="LOW",
                explanation="Next-gen AI architecture unveiled",
                source="GDELT"
            )
        ]

        market_data = TickerMarketData(ticker="NVDA", change_pct=4.2, current_price=125.0)

        sig_result = self.engine.calculate_signal(ticker, good_signals, market_data)
        self.assertGreater(sig_result["tactical_signal"], 0.40)

        signals_map = {t: 0.0 for t in self.engine.DEFAULT_UNIVERSE}
        signals_map["NVDA"] = sig_result["tactical_signal"]

        base_weights = {t: base_w for t in self.engine.DEFAULT_UNIVERSE}
        raw_targets = self.engine.calculate_target_weights(base_weights, signals_map)
        constrained = self.engine.apply_constraints(raw_targets, min_weight=0.02, max_weight=0.15)
        actions = self.engine.generate_actions(base_weights, constrained)

        self.assertGreater(constrained["NVDA"], base_w)
        self.assertEqual(actions["NVDA"], RebalanceAction.INCREASE)

        explanation = self.engine.generate_explanations(
            "NVDA", base_w, constrained["NVDA"], sig_result, actions["NVDA"]
        )
        self.assertIn("Weight increased", explanation)
        self.assertIn("Earnings", explanation)

    def test_05_unchanged_signals_result_in_hold(self):
        """Prove that near-neutral signals produce HOLD action within threshold."""
        neutral_signals = {t: 0.0 for t in self.engine.DEFAULT_UNIVERSE}
        base_weights = {t: 1.0 / 15 for t in self.engine.DEFAULT_UNIVERSE}

        raw_targets = self.engine.calculate_target_weights(base_weights, neutral_signals)
        constrained = self.engine.apply_constraints(raw_targets, min_weight=0.02, max_weight=0.15)
        actions = self.engine.generate_actions(base_weights, constrained, threshold=0.0025)

        for ticker in self.engine.DEFAULT_UNIVERSE:
            self.assertEqual(actions[ticker], RebalanceAction.HOLD)
            self.assertAlmostEqual(constrained[ticker], base_weights[ticker], places=4)

    def test_06_missing_signals_handled_safely(self):
        """Prove that when no news signals exist for a stock or all stocks, engine functions safely without crashing."""
        # Null and empty signal inputs
        empty_res = self.engine.calculate_signal("MSFT", signals=None, market_data=None)
        self.assertEqual(empty_res["avg_sentiment"], 0.0)
        self.assertEqual(empty_res["avg_impact"], 5.0)
        self.assertEqual(empty_res["dominant_event"], "Other")
        self.assertEqual(empty_res["signal_count"], 0)
        self.assertEqual(empty_res["tactical_signal"], 0.0)

        # Full rebalance run with zero signals
        summary = self.engine.rebalance(signals_by_ticker={})
        self.assertEqual(summary.universe_size, 15)
        self.assertAlmostEqual(summary.total_target_weight_pct, 100.0, places=1)
        self.assertLessEqual(summary.turnover_pct, 5.0)
        self.assertEqual(len(summary.constituents), 15)
        for c in summary.constituents:
            self.assertIn(c.rebalance_action, [RebalanceAction.HOLD, RebalanceAction.INCREASE, RebalanceAction.REDUCE])
            self.assertIsNotNone(c.explanation)

    def test_07_no_random_behavior_exists(self):
        """Prove strict mathematical determinism: identical inputs produce identical target weights and explanations."""
        test_signals = {
            "AAPL": [
                RiskSignal(company="AAPL", event_type="Earnings", sentiment_score=0.6, impact_score=6.5, risk_level="LOW", explanation="Beat", source="GDELT")
            ],
            "TSLA": [
                RiskSignal(company="TSLA", event_type="Supply Chain", sentiment_score=-0.7, impact_score=8.0, risk_level="HIGH", explanation="Delay", source="GDELT")
            ]
        }

        run1 = self.engine.rebalance(signals_by_ticker=test_signals)
        run2 = self.engine.rebalance(signals_by_ticker=test_signals)

        self.assertEqual(run1.turnover_pct, run2.turnover_pct)
        self.assertEqual(run1.actions_count, run2.actions_count)

        for c1, c2 in zip(run1.constituents, run2.constituents):
            self.assertEqual(c1.ticker, c2.ticker)
            self.assertEqual(c1.target_weight, c2.target_weight)
            self.assertEqual(c1.rebalance_action, c2.rebalance_action)
            self.assertEqual(c1.calculated_risk_signal, c2.calculated_risk_signal)
            self.assertEqual(c1.explanation, c2.explanation)

    def test_08_turnover_limit_enforcement(self):
        """Prove that max_turnover constraint successfully caps portfolio turnover."""
        extreme_signals = {
            "AAPL": [RiskSignal(company="AAPL", event_type="Earnings", sentiment_score=1.0, impact_score=9.0, risk_level="LOW", explanation="Peak", source="GDELT")],
            "NVDA": [RiskSignal(company="NVDA", event_type="Product Launch", sentiment_score=1.0, impact_score=9.0, risk_level="LOW", explanation="Peak", source="GDELT")],
            "TSLA": [RiskSignal(company="TSLA", event_type="Credit Event", sentiment_score=-1.0, impact_score=9.5, risk_level="CRITICAL", explanation="Crisis", source="GDELT")]
        }

        # Unconstrained turnover
        unconstrained = self.engine.rebalance(
            signals_by_ticker=extreme_signals,
            config=RebalanceRequest(max_turnover=None)
        )

        # Constrained turnover capped at 2.0%
        constrained = self.engine.rebalance(
            signals_by_ticker=extreme_signals,
            config=RebalanceRequest(max_turnover=0.02)
        )

        self.assertLessEqual(constrained.turnover_pct, 2.01)
        self.assertLess(constrained.turnover_pct, unconstrained.turnover_pct)

if __name__ == "__main__":
    unittest.main()
