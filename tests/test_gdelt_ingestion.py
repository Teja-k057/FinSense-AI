import unittest
from unittest.mock import patch, MagicMock
import httpx
from datetime import datetime

from backend.app.ingestion.adapters.gdelt_adapter import GDELTNewsAdapter
from backend.app.ingestion.models import NewsDocument, AcquisitionSummary

class TestGDELTNewsAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = GDELTNewsAdapter(timeout_seconds=2, max_retries=2)
        self.adapter.clear_seen_cache()

    @patch("httpx.Client.get")
    def test_01_successful_ingestion_and_normalization(self, mock_get):
        """Test successful GDELT response normalization into NewsDocument schema."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''{
            "articles": [
                {
                    "title": "JPMorgan Chase &amp; Co. expands commercial lending portfolio",
                    "url": "https://www.reuters.com/business/jpm-lending-expansion",
                    "domain": "reuters.com",
                    "seendate": "20240315T143000Z",
                    "sourcecountry": "United States",
                    "language": "English"
                },
                {
                    "title": "NVIDIA announces new enterprise GPU clusters for datacenter scale",
                    "url": "https://www.bloomberg.com/news/nvda-gpu-datacenter",
                    "domain": "bloomberg.com",
                    "seendate": "20240315150000",
                    "sourcecountry": "United States",
                    "language": "English"
                }
            ]
        }'''
        mock_get.return_value = mock_response

        summary = self.adapter.fetch_news(query="banking OR GPU", timespan="6h", max_records=10)

        self.assertIsInstance(summary, AcquisitionSummary)
        self.assertEqual(summary.source, "GDELT")
        self.assertEqual(summary.status, "SUCCESS_LIVE")
        self.assertFalse(summary.is_fallback)
        self.assertEqual(summary.record_count, 2)
        self.assertEqual(len(summary.records), 2)

        # Validate first document
        doc1 = summary.records[0]
        self.assertIsInstance(doc1, NewsDocument)
        # HTML unescape verification (&amp; -> &)
        self.assertEqual(doc1.title, "JPMorgan Chase & Co. expands commercial lending portfolio")
        self.assertEqual(doc1.url, "https://www.reuters.com/business/jpm-lending-expansion")
        self.assertEqual(doc1.domain, "reuters.com")
        self.assertEqual(doc1.source, "GDELT")
        self.assertEqual(doc1.query_used, "banking OR GPU")
        self.assertIsNotNone(doc1.id)
        self.assertEqual(doc1.published_at.year, 2024)
        self.assertEqual(doc1.published_at.month, 3)
        self.assertEqual(doc1.published_at.day, 15)

    @patch("httpx.Client.get")
    def test_02_duplicate_article_filtering(self, mock_get):
        """Test deduplication prevents identical articles within same batch and across calls."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Same URL and title returned twice in single response
        mock_response.text = '''{
            "articles": [
                {
                    "title": "Federal Reserve leaves benchmark interest rates steady",
                    "url": "https://www.wsj.com/economy/fed-decision-steady",
                    "domain": "wsj.com",
                    "seendate": "20240315140000"
                },
                {
                    "title": "Federal Reserve leaves benchmark interest rates steady",
                    "url": "https://www.wsj.com/economy/fed-decision-steady",
                    "domain": "wsj.com",
                    "seendate": "20240315140000"
                }
            ]
        }'''
        mock_get.return_value = mock_response

        summary1 = self.adapter.fetch_news(query="fed rates", max_records=10)
        self.assertEqual(summary1.record_count, 1, "Duplicate in same batch must be filtered")

        # Second call with same article should also be filtered by seen cache
        summary2 = self.adapter.fetch_news(query="fed rates", max_records=10)
        self.assertEqual(summary2.record_count, 0, "Already seen article across calls must be filtered")
        self.assertEqual(summary2.status, "EMPTY")

    @patch("httpx.Client.get")
    def test_03_empty_articles_response(self, mock_get):
        """Test graceful handling when GDELT returns 0 articles without fabrication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"articles": []}'
        mock_get.return_value = mock_response

        summary = self.adapter.fetch_news(query="obscure keyword", max_records=10)
        self.assertEqual(summary.record_count, 0)
        self.assertEqual(summary.status, "EMPTY")
        self.assertFalse(summary.is_fallback)
        self.assertEqual(len(summary.records), 0, "Must never fabricate records on empty response")

    @patch("httpx.Client.get")
    def test_04_malformed_json_response_handling(self, mock_get):
        """Test handling of non-JSON / HTML error pages from GDELT."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><head><title>504 Gateway Time-out</title></head><body>Server Busy</body></html>'
        mock_get.return_value = mock_response

        summary = self.adapter.fetch_news(query="stocks", max_records=10)
        self.assertEqual(summary.status, "ERROR")
        self.assertEqual(summary.record_count, 0)
        self.assertIn("Invalid JSON payload", summary.error_message)
        self.assertEqual(len(summary.records), 0)

    @patch("httpx.Client.get")
    def test_05_http_server_error_and_retries(self, mock_get):
        """Test HTTP 500 error triggers retries and records error cleanly without fabrication."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = 'Service Temporarily Unavailable'
        mock_get.return_value = mock_response

        summary = self.adapter.fetch_news(query="earnings", max_records=5)
        self.assertEqual(mock_get.call_count, self.adapter.max_retries)
        self.assertEqual(summary.status, "ERROR")
        self.assertEqual(summary.record_count, 0)
        self.assertIn("HTTP 503", summary.error_message)

    @patch("httpx.Client.get")
    def test_06_timeout_exception_handling(self, mock_get):
        """Test network timeout triggers retries and returns clean error summary."""
        mock_get.side_effect = httpx.TimeoutException("Handshake operation timed out")

        summary = self.adapter.fetch_news(query="inflation", max_records=5)
        self.assertEqual(mock_get.call_count, self.adapter.max_retries)
        self.assertEqual(summary.status, "ERROR")
        self.assertEqual(summary.record_count, 0)
        self.assertIn("TimeoutException", summary.error_message)
        self.assertEqual(len(summary.records), 0)

    def test_07_timestamp_parsing_variants(self):
        """Test parsing of different GDELT seendate timestamp representations."""
        # 14-digit format: YYYYMMDDHHMMSS
        t1 = self.adapter._parse_gdelt_timestamp("20240315123045")
        self.assertEqual(t1.year, 2024)
        self.assertEqual(t1.month, 3)
        self.assertEqual(t1.day, 15)
        self.assertEqual(t1.hour, 12)
        self.assertEqual(t1.minute, 30)

        # ISO-like format with T and Z: 20240315T123045Z
        t2 = self.adapter._parse_gdelt_timestamp("20240315T123045Z")
        self.assertEqual(t2.year, 2024)
        self.assertEqual(t2.hour, 12)

        # Date only: 8-digit format YYYYMMDD
        t3 = self.adapter._parse_gdelt_timestamp("20240315")
        self.assertEqual(t3.year, 2024)
        self.assertEqual(t3.day, 15)

if __name__ == "__main__":
    unittest.main()
