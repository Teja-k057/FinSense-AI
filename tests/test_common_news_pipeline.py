import unittest
from datetime import datetime, timezone
from backend.app.preprocessing.pipeline import CommonNewsPipeline
from backend.app.ingestion.models import NewsDocument

class TestCommonNewsPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = CommonNewsPipeline()
        self.pipeline.clear_seen_cache()

    def test_01_both_sources_produce_identical_canonical_schema(self):
        """Prove that GDELT and Kaggle inputs both normalize into the identical NewsDocument schema."""
        raw_gdelt = {
            "title": "JPMorgan Chase &amp; Co. expands commercial credit facilities",
            "text": "JPMorgan Chase announced today it is expanding commercial lending capacity.",
            "url": "https://www.reuters.com/business/jpm-expansion",
            "domain": "reuters.com",
            "seendate": "20240315143000"
        }

        raw_kaggle = {
            "headline": "Operating profit at Nokia rose to EUR 14.2 mn from EUR 9.1 mn .",
            "raw_sentiment_label": "positive",
            "url": None,
            "date": "2024-03-15T10:00:00Z"
        }

        doc_gdelt = self.pipeline.process_raw_item(raw_gdelt, source="GDELT")
        doc_kaggle = self.pipeline.process_raw_item(raw_kaggle, source="Kaggle")

        # 1. Both must be instances of the canonical NewsDocument
        self.assertIsInstance(doc_gdelt, NewsDocument)
        self.assertIsInstance(doc_kaggle, NewsDocument)

        # 2. Both must share identical top-level fields
        expected_fields = {
            "id", "source", "title", "text", "url", "publication_time",
            "retrieved_time", "company_entities", "original_label", "domain",
            "language", "query_used", "metadata"
        }
        self.assertEqual(set(doc_gdelt.model_dump().keys()), expected_fields)
        self.assertEqual(set(doc_kaggle.model_dump().keys()), expected_fields)

        # 3. Source tracking verification
        self.assertEqual(doc_gdelt.source, "GDELT")
        self.assertEqual(doc_kaggle.source, "Kaggle")

    def test_02_text_cleaning_and_html_noise_removal(self):
        """Test HTML stripping, entity unescaping, and financial contraction expansion."""
        dirty_input = "  <p><b>Apple Inc.</b> &amp; suppliers report $500M profit surge in Q1'24. Visit https://news.com/aapl </p>  "
        cleaned = self.pipeline.clean_text(dirty_input)

        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("<b>", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertIn("Apple Inc. & suppliers", cleaned)
        self.assertIn("Q1 2024", cleaned)

    def test_03_duplicate_detection(self):
        """Test deduplication drops exact duplicate documents."""
        raw_doc = {
            "title": "Federal Reserve maintains interest rate corridor steady",
            "url": "https://wsj.com/fed-decision-2024"
        }

        first_pass = self.pipeline.process_raw_item(raw_doc, source="GDELT")
        self.assertIsNotNone(first_pass)

        second_pass = self.pipeline.process_raw_item(raw_doc, source="GDELT")
        self.assertIsNone(second_pass, "Duplicate item must be rejected and return None")

    def test_04_missing_value_handling(self):
        """Test missing publication time, URL, or domain resolve gracefully without failing."""
        raw_doc = {
            "title": "Boeing announces delivery schedule update for commercial aircraft",
            # url, date, domain omitted
        }

        doc = self.pipeline.process_raw_item(raw_doc, source="GDELT")
        self.assertIsNotNone(doc)
        self.assertIsNone(doc.url)
        self.assertEqual(doc.domain, "Unknown")
        self.assertIsInstance(doc.publication_time, datetime)
        self.assertIsNotNone(doc.publication_time.tzinfo)

    def test_05_timestamp_normalization(self):
        """Test normalizing diverse timestamp representations into UTC datetime."""
        # GDELT 14-digit format: YYYYMMDDHHMMSS
        ts1 = self.pipeline.normalize_timestamp("20240315120000")
        self.assertEqual(ts1.year, 2024)
        self.assertEqual(ts1.month, 3)
        self.assertEqual(ts1.day, 15)
        self.assertEqual(ts1.hour, 12)
        self.assertEqual(ts1.tzinfo, timezone.utc)

        # Standard ISO-8601 string
        ts2 = self.pipeline.normalize_timestamp("2024-03-15T14:30:00Z")
        self.assertEqual(ts2.year, 2024)
        self.assertEqual(ts2.hour, 14)
        self.assertEqual(ts2.minute, 30)

        # None / invalid input falls back to current time without crashing
        ts3 = self.pipeline.normalize_timestamp(None)
        self.assertIsInstance(ts3, datetime)

    def test_06_quality_and_noise_filtering(self):
        """Test filtering out low quality text fragments and navigation error pages."""
        # Too short (< 10 chars)
        self.assertFalse(self.pipeline.is_valid_quality("Hi", "short"))

        # Error / placeholder pages
        self.assertFalse(self.pipeline.is_valid_quality("404 Not Found", "Page requested does not exist"))
        self.assertFalse(self.pipeline.is_valid_quality("Subscribe to read full story", "Access denied for non-subscribers"))

        # Valid financial content
        self.assertTrue(self.pipeline.is_valid_quality("NVIDIA posts record quarterly data center revenue", "NVIDIA Corp. reported earnings today."))

    def test_07_company_entity_extraction_preparation(self):
        """Test that company/ticker candidate mentions are extracted into company_entities."""
        raw_doc = {
            "title": "Tesla and Apple deepen autonomous hardware collaboration with NVIDIA",
            "url": "https://techcrunch.com/tsla-aapl-nvda"
        }

        doc = self.pipeline.process_raw_item(raw_doc, source="GDELT")
        self.assertIsNotNone(doc)
        self.assertIn("TSLA", doc.company_entities)
        self.assertIn("AAPL", doc.company_entities)
        self.assertIn("NVDA", doc.company_entities)

    def test_08_original_label_preservation(self):
        """Test that ground-truth sentiment labels are preserved for Kaggle and omitted for GDELT."""
        # Kaggle with authentic ground-truth
        raw_kaggle = {
            "title": "Company revenue climbed 25 percent exceeding Wall Street estimates",
            "raw_sentiment_label": "positive"
        }
        doc_kaggle = self.pipeline.process_raw_item(raw_kaggle, source="Kaggle")
        self.assertEqual(doc_kaggle.original_label, "positive")
        self.assertTrue(doc_kaggle.metadata["has_ground_truth_label"])

        # GDELT without ground truth (never fabricate!)
        raw_gdelt = {
            "title": "Global energy markets react to OPEC crude production announcement"
        }
        doc_gdelt = self.pipeline.process_raw_item(raw_gdelt, source="GDELT")
        self.assertIsNone(doc_gdelt.original_label, "GDELT must not fabricate original_label")
        self.assertFalse(doc_gdelt.metadata["has_ground_truth_label"])

if __name__ == "__main__":
    unittest.main()
