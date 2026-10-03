import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.preprocessing.text_cleaner import TextCleaner
from backend.app.preprocessing.entity_resolver import EntityResolver
from backend.app.nlp.sentiment import FinancialSentimentEngine
from backend.app.nlp.event_classifier import FinancialEventClassifier
from backend.app.nlp.impact_scorer import FinancialImpactScorer
from backend.app.stress_testing.metrics import RiskMetricsCalculator

class SystemIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_and_health(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "online")

        h_resp = self.client.get("/api/v1/health")
        self.assertEqual(h_resp.status_code, 200)
        data = h_resp.json()["data"]
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database_status"], "connected")

    def test_text_cleaning_and_entities(self):
        raw = "   <b>JPMorgan</b>  faces $500M penalty in Q1'24 over loan loss provisions...   "
        cleaned = TextCleaner.clean(raw)
        self.assertNotIn("<b>", cleaned)
        self.assertIn("Q1 2024", cleaned)

        entity = EntityResolver.resolve(cleaned)
        self.assertEqual(entity["ticker"], "JPM")
        self.assertEqual(entity["sector"], "Financials")

    def test_nlp_sentiment_bounds(self):
        engine = FinancialSentimentEngine()
        res_neg = engine.analyze("Severe credit downgrade, massive bankruptcy losses and default")
        self.assertLess(res_neg["score"], 0.0)
        self.assertGreaterEqual(res_neg["score"], -1.0)
        self.assertEqual(res_neg["label"], "Negative")

        res_pos = engine.analyze("Record revenue surge, massive profit gains and upgrade")
        self.assertGreater(res_pos["score"], 0.0)
        self.assertLessEqual(res_pos["score"], 1.0)
        self.assertEqual(res_pos["label"], "Positive")

    def test_event_classification_and_impact(self):
        ev = FinancialEventClassifier.classify("Bank reports major liquidity crunch and default risk")
        self.assertEqual(ev["event_type"], "Credit Event")
        self.assertGreaterEqual(ev["confidence"], 0.5)

        impact = FinancialImpactScorer.calculate(
            sentiment_score=-0.85,
            event_severity_weight=ev["severity_weight"],
            ticker="JPM"
        )
        self.assertGreaterEqual(impact["impact_score"], 1.0)
        self.assertLessEqual(impact["impact_score"], 10.0)

    def test_stress_testing_math_invariants(self):
        metrics = RiskMetricsCalculator.calculate_var_cvar(
            portfolio_value=10_000_000.0,
            portfolio_volatility_annual=0.20,
            confidence=0.95
        )
        self.assertGreater(metrics["var_dollars"], 0.0)
        self.assertGreaterEqual(metrics["cvar_dollars"], metrics["var_dollars"])

    def test_stress_api_simulation(self):
        payload = {
            "portfolio_id": "default",
            "scenario": "HISTORICAL_2008",
            "confidence_level": 0.95
        }
        resp = self.client.post("/api/v1/stress-test/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("pnl_loss_amount", data)
        self.assertIn("post_var_95", data)
        self.assertGreater(len(data["asset_breakdown"]), 0)

if __name__ == "__main__":
    unittest.main()
