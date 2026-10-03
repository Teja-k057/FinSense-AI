import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from backend.app.ingestion.adapters.kaggle_adapter import (
    KaggleNewsAdapter,
    KaggleCredentialsRequiredError,
    CorruptedDatasetError
)
from backend.app.ingestion.models import NewsDocument, AcquisitionSummary

class TestKaggleNewsAdapter(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.cache_file = self.test_dir / "test_phrasebank.csv"
        self.adapter = KaggleNewsAdapter(
            public_url="https://mock.kaggle.com/test-phrasebank.csv",
            cache_file=self.cache_file
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("httpx.Client.get")
    def test_01_successful_acquisition_and_ground_truth_preservation(self, mock_get):
        """Test successful public acquisition, column mapping, and authentic label preservation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Financial PhraseBank CSV format: "sentiment, headline"
        csv_content = (
            'positive,"Operating profit rose to EUR 13.1 mn from EUR 8.7 mn in the corresponding period of 2007 ."\n'
            'negative,"Net sales decreased by 7 % to EUR 125.8 mn from EUR 135.3 mn ."\n'
            'neutral,"The company has no plans to move production to other regions ."\n'
        ) * 50  # Repeat to exceed min payload threshold
        mock_response.content = csv_content.encode("utf-8")
        mock_response.text = csv_content
        mock_get.return_value = mock_response

        summary = self.adapter.acquire(limit=5)

        self.assertIsInstance(summary, AcquisitionSummary)
        self.assertEqual(summary.source, "Kaggle")
        self.assertEqual(summary.status, "SUCCESS_LIVE")
        self.assertFalse(summary.is_fallback)
        self.assertEqual(summary.record_count, 5)
        self.assertTrue(self.cache_file.exists(), "Downloaded dataset must be cached locally")

        # Verify record normalization & ground truth
        doc0 = summary.records[0]
        self.assertIsInstance(doc0, NewsDocument)
        self.assertIn("Operating profit rose", doc0.title)
        self.assertEqual(doc0.source, "Kaggle")
        self.assertEqual(doc0.metadata["ground_truth_sentiment"], "positive")
        self.assertTrue(doc0.metadata["has_ground_truth_sentiment"])

        # Explicitly verify missing labels are reported, not fabricated
        self.assertIsNone(doc0.metadata["ground_truth_event"])
        self.assertFalse(doc0.metadata["has_ground_truth_event"])
        self.assertIsNone(doc0.metadata["ground_truth_impact_score"])
        self.assertFalse(doc0.metadata["has_ground_truth_impact"])

    @patch("httpx.Client.get")
    def test_02_cache_reuse_avoids_repeated_downloads(self, mock_get):
        """Test local cache reuse on repeated acquisition runs without triggering network calls."""
        # Seed local cache with valid dummy dataset >= 50KB
        dummy_line = 'positive,"Company reports quarterly expansion across all segments ."\n'
        content = (dummy_line * 1000).encode("utf-8")
        self.cache_file.write_bytes(content)

        summary = self.adapter.acquire(limit=10, force_download=False)

        self.assertEqual(summary.status, "SUCCESS_CACHED")
        self.assertEqual(summary.record_count, 10)
        self.assertEqual(mock_get.call_count, 0, "Cached dataset must not trigger HTTP network request")

    def test_03_missing_credentials_handling(self):
        """Test missing credentials for authenticated Kaggle operations raises explicit error."""
        self.adapter.kaggle_username = None
        self.adapter.kaggle_key = None

        with self.assertRaises(KaggleCredentialsRequiredError) as ctx:
            self.adapter._acquire_internal(limit=10, force_download=False, require_auth=True)

        self.assertIn("Kaggle API authentication is required", str(ctx.exception))
        self.assertIn("KAGGLE_USERNAME and KAGGLE_KEY", str(ctx.exception))

    @patch("httpx.Client.get")
    def test_04_corrupted_download_html_response(self, mock_get):
        """Test corrupted download (e.g. 404 HTML body) is detected and rejected without caching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>Error</body></html>" * 20
        mock_response.text = mock_response.content.decode()
        mock_get.return_value = mock_response

        summary = self.adapter.acquire(limit=10, force_download=True)

        self.assertEqual(summary.status, "ERROR")
        self.assertEqual(summary.record_count, 0)
        self.assertIn("HTML error page", summary.error_message)

    def test_05_malformed_empty_dataset(self):
        """Test malformed empty CSV raises CorruptedDatasetError."""
        self.cache_file.write_text(",,,,\n\n\n", encoding="utf-8")

        with self.assertRaises(CorruptedDatasetError):
            self.adapter._parse_and_validate_file(self.cache_file, limit=10)

if __name__ == "__main__":
    unittest.main()
