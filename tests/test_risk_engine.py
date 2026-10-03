import unittest
from datetime import datetime
from backend.app.nlp.sentiment import FinancialSentimentEngine
from backend.app.nlp.event_classifier import FinancialEventClassifier
from backend.app.nlp.impact_scorer import FinancialImpactScorer
from backend.app.risk_engine.signals import RiskSignalEngine
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.ingestion.models import NewsDocument

class TestUnifiedRiskEngine(unittest.TestCase):
    """
    Test suite validating the core AI/NLP Risk Engine:
    - Score ranges: Sentiment in [-1.0, 1.0], Impact in [1.0, 10.0]
    - Classification validity: Controlled 10-class taxonomy
    - Deterministic impact scoring
    - Missing text handling
    - Duplicate event detection
    - Canonical RiskSignal schema
    """

    def setUp(self):
        self.sentiment_engine = FinancialSentimentEngine()
        self.event_classifier = FinancialEventClassifier()
        self.risk_engine = RiskSignalEngine()
        self.risk_engine.reset_duplicate_cache()

    def test_01_sentiment_score_ranges(self):
        """Test sentiment score is strictly bound within [-1.0, +1.0] across edge cases."""
        samples = [
            "Massive bankruptcy losses, severe debt default, and catastrophic decline",
            "Record surging revenues, immense profit gains, and upgrade outperformance",
            "The committee held its regular monthly session in Geneva.",
            "Extreme crisis collapse drop fail penalty fine fraud",
            "Outstanding bullish growth dividend rally surge beat"
        ]

        for text in samples:
            res = self.sentiment_engine.analyze(text)
            score = res["score"]
            self.assertGreaterEqual(score, -1.0, f"Score below -1.0: {score} for '{text}'")
            self.assertLessEqual(score, 1.0, f"Score above +1.0: {score} for '{text}'")
            self.assertIn(res["label"], ["Positive", "Negative", "Neutral"])
            self.assertIn("explanation", res)

    def test_02_impact_score_ranges(self):
        """Test impact score is strictly bound within [1.0, 10.0] across extreme inputs."""
        test_inputs = [
            {"sentiment": -1.0, "severity": 1.0, "ticker": "JPM", "event": "Credit Event"},
            {"sentiment": 1.0, "severity": 1.0, "ticker": "AAPL", "event": "Earnings"},
            {"sentiment": 0.0, "severity": 0.1, "ticker": "GENERAL", "event": "Other"},
            {"sentiment": -0.99, "severity": 0.95, "ticker": "NVDA", "event": "Cybersecurity"},
            {"sentiment": 0.05, "severity": 0.40, "ticker": "BA", "event": "Other"}
        ]

        for item in test_inputs:
            res = FinancialImpactScorer.calculate(
                sentiment_score=item["sentiment"],
                event_severity_weight=item["severity"],
                ticker=item["ticker"],
                event_type=item["event"]
            )
            score = res["impact_score"]
            self.assertGreaterEqual(score, 1.0, f"Impact below 1.0: {score}")
            self.assertLessEqual(score, 10.0, f"Impact above 10.0: {score}")
            self.assertIn(res["risk_level"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            # Methodology disclaimer check
            self.assertIn("Hackathon", res["explanation"])

    def test_03_classification_validity_across_taxonomy(self):
        """Verify that classification maps accurately to the 10 controlled taxonomy classes."""
        expected_taxonomy = set(FinancialEventClassifier.CONTROLLED_TAXONOMY)
        self.assertEqual(len(expected_taxonomy), 10)

        test_cases = [
            ("U.S. imposes new tariff sanctions amidst escalating military conflict", "Geopolitical"),
            ("Federal Reserve announces 50 bps interest rate hike to tame inflation", "Macroeconomic"),
            ("Regional bank faces insolvency, defaulting on debt bonds after credit downgrade", "Credit Event"),
            ("Microsoft completes $69 billion acquisition and takeover buyout", "Merger/Acquisition"),
            ("Apple unveils flagship next-gen AI device at annual product launch", "Product Launch"),
            ("SEC initiates antitrust probe and issues subpoena penalty fine against tech giant", "Regulatory"),
            ("NVIDIA reports record quarterly profit surge, beating revenue guidance estimates", "Earnings"),
            ("Automaker announces factory shutdown due to critical semiconductor supply chain bottleneck", "Supply Chain"),
            ("Major defense contractor hit by ransomware data breach and cyberattack", "Cybersecurity"),
            ("Local library hosts weekend book reading event", "Other")
        ]

        for text, expected_category in test_cases:
            res = self.event_classifier.classify(text)
            actual_cat = res["event_type"]
            self.assertIn(actual_cat, expected_taxonomy, f"Category '{actual_cat}' not in taxonomy")
            self.assertEqual(actual_cat, expected_category, f"Failed for '{text}': got '{actual_cat}', expected '{expected_category}'")
            self.assertGreaterEqual(res["confidence"], 0.0)
            self.assertLessEqual(res["confidence"], 1.0)

    def test_04_deterministic_impact_scoring(self):
        """Test that identical inputs generate bitwise deterministic impact scores and explanations."""
        res1 = FinancialImpactScorer.calculate(
            sentiment_score=-0.75,
            event_severity_weight=0.85,
            ticker="JPM",
            event_type="Credit Event"
        )
        res2 = FinancialImpactScorer.calculate(
            sentiment_score=-0.75,
            event_severity_weight=0.85,
            ticker="JPM",
            event_type="Credit Event"
        )

        self.assertEqual(res1["impact_score"], res2["impact_score"])
        self.assertEqual(res1["risk_level"], res2["risk_level"])
        self.assertEqual(res1["factor_breakdown"], res2["factor_breakdown"])
        self.assertEqual(res1["explanation"], res2["explanation"])

        # Monotonicity test: higher severity + higher magnitude should yield higher or equal impact
        res_mild = FinancialImpactScorer.calculate(
            sentiment_score=-0.10,
            event_severity_weight=0.40,
            ticker="JPM",
            event_type="Other"
        )
        self.assertGreater(res1["impact_score"], res_mild["impact_score"])

    def test_05_missing_and_empty_text_handling(self):
        """Verify engine gracefully handles missing, empty, or whitespace-only inputs without crashing."""
        edge_inputs = [None, "", "    ", "\n\t  "]

        for inp in edge_inputs:
            signal = self.risk_engine.process_text(inp, source="TestRunner")
            self.assertIsInstance(signal, RiskSignal)
            self.assertEqual(signal.sentiment_score, 0.0)
            self.assertEqual(signal.impact_score, 1.0)
            self.assertEqual(signal.risk_level, "LOW")
            self.assertEqual(signal.event_type, "Other")
            self.assertIn("No input text provided", signal.explanation)

    def test_06_duplicate_event_detection(self):
        """Verify that identical events are flagged as duplicates and filtered during batch processing."""
        headline = "JPMorgan reports major credit default losses on commercial real estate loans"

        sig1 = self.risk_engine.process_text(headline, source="GDELT", ticker_hint="JPM")
        self.assertFalse(sig1.is_duplicate, "First event should not be marked duplicate")

        sig2 = self.risk_engine.process_text(headline, source="GDELT", ticker_hint="JPM")
        self.assertTrue(sig2.is_duplicate, "Second identical event should be marked duplicate")

        # Test batch processing skips duplicates
        doc1 = NewsDocument(
            id="doc1",
            source="GDELT",
            title="Apple unveils new AI chip",
            text="Apple unveiled its next-gen M4 processor at launch event.",
            company_entities=["AAPL"]
        )
        doc2 = NewsDocument(
            id="doc2",
            source="GDELT",
            title="Apple unveils new AI chip",
            text="Apple unveiled its next-gen M4 processor at launch event.",
            company_entities=["AAPL"]
        )

        batch_signals = self.risk_engine.process_batch([doc1, doc2], skip_duplicates=True)
        # Should only contain 1 signal because the second was deduplicated
        self.assertEqual(len(batch_signals), 1)

    def test_07_structured_risk_signal_contract(self):
        """Verify the output RiskSignal matches all 8 required schema fields."""
        text = "Tesla faces massive supply chain bottleneck at Berlin Gigafactory, reducing vehicle deliveries"
        signal = self.risk_engine.process_text(text, source="GDELT", ticker_hint="TSLA")

        # Verify 8 exact fields required by prompt:
        # {company, event_type, sentiment_score, impact_score, risk_level, explanation, source, timestamp}
        d = signal.model_dump()
        self.assertIn("company", d)
        self.assertIn("event_type", d)
        self.assertIn("sentiment_score", d)
        self.assertIn("impact_score", d)
        self.assertIn("risk_level", d)
        self.assertIn("explanation", d)
        self.assertIn("source", d)
        self.assertIn("timestamp", d)

        self.assertEqual(signal.company, "TSLA")
        self.assertEqual(signal.event_type, "Supply Chain")
        self.assertLess(signal.sentiment_score, 0.0)
        self.assertGreaterEqual(signal.impact_score, 1.0)
        self.assertLessEqual(signal.impact_score, 10.0)
        self.assertEqual(signal.source, "GDELT")
        self.assertIsInstance(signal.timestamp, datetime)

    def test_08_both_sources_produce_identical_signals(self):
        """Verify that GDELT and Kaggle canonical documents seamlessly generate RiskSignals."""
        doc_gdelt = NewsDocument(
            id="gdelt_001",
            source="GDELT",
            title="Bank of America quarterly profits surge 15%",
            text="Bank of America reported strong revenue gains and net interest income beat.",
            company_entities=["BAC"]
        )

        doc_kaggle = NewsDocument(
            id="kaggle_001",
            source="Kaggle",
            title="Operating profit rose to EUR 14.2 mn",
            text="Operating profit rose to EUR 14.2 mn from EUR 9.1 mn as sales climbed.",
            company_entities=["BAC"]
        )

        signals_gdelt = self.risk_engine.process_document(doc_gdelt)
        signals_kaggle = self.risk_engine.process_document(doc_kaggle)

        self.assertEqual(len(signals_gdelt), 1)
        self.assertEqual(len(signals_kaggle), 1)

        sig_g = signals_gdelt[0]
        sig_k = signals_kaggle[0]

        self.assertEqual(sig_g.source, "GDELT")
        self.assertEqual(sig_k.source, "Kaggle")
        self.assertEqual(sig_g.event_type, "Earnings")
        self.assertEqual(sig_k.event_type, "Earnings")
        self.assertGreater(sig_g.sentiment_score, 0.0)
        self.assertGreater(sig_k.sentiment_score, 0.0)

if __name__ == "__main__":
    unittest.main()
