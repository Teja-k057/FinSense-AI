import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestFastAPIRiskSignalAPI(unittest.TestCase):
    """
    Test suite for Step 7: FastAPI Risk Signal API.
    Validates:
    1. GET /health
    2. GET /news
    3. GET /risk-signals
    4. GET /risk-signals/{company}
    5. POST /analyze
    6. GET /companies
    7. GET /events
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_get_health(self):
        """Test GET /health returns 200 OK with all operational components."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["components"]["sentiment_engine"], "operational")
        self.assertEqual(data["components"]["event_classifier"], "operational")
        self.assertEqual(data["components"]["impact_scorer"], "operational")

    def test_02_get_news_with_pagination_and_filtering(self):
        """Test GET /news pagination, multi-criteria filtering, and response schema."""
        # 1. Basic pagination
        resp = self.client.get("/news?limit=5&offset=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["offset"], 0)
        self.assertIsInstance(data["items"], list)

        # 2. Source filter
        resp_gdelt = self.client.get("/news?source=GDELT&limit=5")
        self.assertEqual(resp_gdelt.status_code, 200)
        for item in resp_gdelt.json()["items"]:
            self.assertEqual(item["source"], "GDELT")

        # 3. Company filter
        resp_comp = self.client.get("/news?company=JPM&limit=5")
        self.assertEqual(resp_comp.status_code, 200)

    def test_03_get_risk_signals_multi_filtering(self):
        """Test GET /risk-signals returns structured signals with filtering."""
        resp = self.client.get("/risk-signals?limit=10&offset=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertIsInstance(data["items"], list)

        if data["items"]:
            sig = data["items"][0]
            # Verify 8 required fields
            self.assertIn("company", sig)
            self.assertIn("sentiment_score", sig)
            self.assertIn("event_type", sig)
            self.assertIn("impact_score", sig)
            self.assertIn("risk_level", sig)
            self.assertIn("explanation", sig)
            self.assertIn("source", sig)
            self.assertIn("timestamp", sig)

            self.assertGreaterEqual(sig["sentiment_score"], -1.0)
            self.assertLessEqual(sig["sentiment_score"], 1.0)
            self.assertGreaterEqual(sig["impact_score"], 1.0)
            self.assertLessEqual(sig["impact_score"], 10.0)

        # Filtering by min_impact
        resp_filtered = self.client.get("/risk-signals?min_impact=5.0&limit=5")
        self.assertEqual(resp_filtered.status_code, 200)
        for s in resp_filtered.json()["items"]:
            self.assertGreaterEqual(s["impact_score"], 5.0)

    def test_04_get_company_risk_signals(self):
        """Test GET /risk-signals/{company} for recognized and unrecognized tickers."""
        # 1. Recognized ticker in universe
        resp = self.client.get("/risk-signals/JPM")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["company"], "JPM")
        self.assertEqual(data["company_name"], "JPMorgan Chase & Co.")
        self.assertEqual(data["sector"], "Financials")
        self.assertIn("total_signals", data)
        self.assertIn("average_sentiment", data)
        self.assertIn("average_impact", data)
        self.assertIn("highest_risk_level", data)
        self.assertIn("event_distribution", data)
        self.assertIsInstance(data["signals"], list)

        # 2. Unknown ticker not in universe
        resp_404 = self.client.get("/risk-signals/UNKNOWN999XYZ")
        self.assertEqual(resp_404.status_code, 404)

    def test_05_post_analyze(self):
        """Test POST /analyze accurately processes raw text and returns structured signal."""
        payload = {
            "text": "Tesla reports critical supply chain bottlenecks and parts shortages at assembly plants",
            "source": "AdHoc",
            "ticker_hint": "TSLA"
        }
        resp = self.client.post("/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        sig = resp.json()

        # Check required fields
        self.assertEqual(sig["company"], "TSLA")
        self.assertEqual(sig["event_type"], "Supply Chain")
        self.assertLess(sig["sentiment_score"], 0.0)
        self.assertGreaterEqual(sig["impact_score"], 1.0)
        self.assertLessEqual(sig["impact_score"], 10.0)
        self.assertIn(sig["risk_level"], ["HIGH", "CRITICAL", "MEDIUM", "LOW"])
        self.assertIn("TSLA", sig["explanation"])
        self.assertEqual(sig["source"], "AdHoc")
        self.assertIsNotNone(sig["timestamp"])

    def test_06_get_companies(self):
        """Test GET /companies returns the 15 mock index companies with metadata."""
        resp = self.client.get("/companies")
        self.assertEqual(resp.status_code, 200)
        companies = resp.json()
        self.assertIsInstance(companies, list)
        self.assertEqual(len(companies), 15)

        tickers = [c["ticker"] for c in companies]
        expected_sample = ["AAPL", "MSFT", "NVDA", "JPM", "XOM", "TSLA"]
        for exp in expected_sample:
            self.assertIn(exp, tickers)

        for c in companies:
            self.assertIn("ticker", c)
            self.assertIn("name", c)
            self.assertIn("sector", c)
            self.assertIn("base_weight_pct", c)
            self.assertIn("signal_count", c)
            self.assertIn("risk_level", c)

    def test_07_get_events(self):
        """Test GET /events returns the 10 controlled taxonomy classes."""
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        events = resp.json()
        self.assertIsInstance(events, list)
        self.assertEqual(len(events), 10)

        event_names = [e["event_type"] for e in events]
        expected_taxonomy = [
            "Geopolitical", "Macroeconomic", "Credit Event", "Merger/Acquisition",
            "Product Launch", "Regulatory", "Earnings", "Supply Chain",
            "Cybersecurity", "Other"
        ]
        for exp in expected_taxonomy:
            self.assertIn(exp, event_names)

        for e in events:
            self.assertIn("event_type", e)
            self.assertIn("description", e)
            self.assertIn("severity_weight", e)
            self.assertIn("signal_count", e)

if __name__ == "__main__":
    unittest.main()
