import csv
import hashlib
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import httpx

from backend.app.config.settings import settings
from backend.app.ingestion.adapters.base import BaseAdapter
from backend.app.ingestion.models import NewsDocument, AcquisitionSummary

logger = logging.getLogger("ingestion.kaggle")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class KaggleCredentialsRequiredError(Exception):
    """Raised when an authenticated Kaggle operation is attempted without credentials in .env."""
    pass

class CorruptedDatasetError(Exception):
    """Raised when downloaded dataset fails integrity or schema validation."""
    pass

class KaggleNewsAdapter(BaseAdapter):
    """
    Automated acquisition adapter for the Kaggle Financial News dataset (Financial PhraseBank).
    - Automatically acquires the open dataset without requiring manual user downloads.
    - Validates file integrity, column schemas, and preserves authentic ground-truth labels.
    - Caches locally to avoid redundant bandwidth consumption.
    - Explicitly identifies missing labels without fabricating ground truth.
    - Strictly obeys credential rules: no invented or hardcoded credentials.
    """

    DATASET_NAME = "Financial PhraseBank (Kaggle / Malo et al. 2014)"
    MIN_EXPECTED_BYTES = 50_000  # Genuine dataset is ~672 KB

    def __init__(
        self,
        public_url: Optional[str] = None,
        cache_file: Optional[Path] = None
    ):
        super().__init__("Kaggle")
        self.public_url = public_url or settings.KAGGLE_PUBLIC_DATASET_URL
        self.cache_file = cache_file or settings.KAGGLE_CACHE_FILE
        self.kaggle_username = settings.KAGGLE_USERNAME
        self.kaggle_key = settings.KAGGLE_KEY

    def acquire(
        self,
        limit: int = 50,
        force_download: bool = False,
        require_auth: bool = False
    ) -> AcquisitionSummary:
        return self.execute_with_timing(
            self._acquire_internal,
            limit=limit,
            force_download=force_download,
            require_auth=require_auth
        )

    def _acquire_internal(
        self,
        limit: int,
        force_download: bool,
        require_auth: bool
    ) -> AcquisitionSummary:
        start_time = time.perf_counter()

        # 1. Credential Check for Authenticated Kaggle Operations
        if require_auth:
            if not self.kaggle_username or not self.kaggle_key:
                err_msg = (
                    "Kaggle API authentication is required for this operation, but credentials are missing. "
                    "Please set KAGGLE_USERNAME and KAGGLE_KEY in your local .env file. "
                    "You can obtain free API tokens at https://www.kaggle.com/settings -> 'Create New Token'."
                )
                logger.error(f"[Kaggle] {err_msg}")
                raise KaggleCredentialsRequiredError(err_msg)

        # 2. Local Cache Check
        if self.cache_file.exists() and not force_download:
            try:
                cache_size = self.cache_file.stat().st_size
                if cache_size >= self.MIN_EXPECTED_BYTES:
                    records, detected_cols = self._parse_and_validate_file(self.cache_file, limit=limit)
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    logger.info(
                        f"[Kaggle] Reused verified local cache: {self.cache_file} "
                        f"({cache_size:,} bytes | {len(records)} records loaded in {duration_ms}ms)."
                    )
                    return AcquisitionSummary(
                        source=self.source_name,
                        record_count=len(records),
                        status="SUCCESS_CACHED",
                        is_fallback=False,
                        error_message=None,
                        duration_ms=duration_ms,
                        query_used=self.DATASET_NAME,
                        acquired_at=utc_now(),
                        records=records
                    )
                else:
                    logger.warning(
                        f"[Kaggle] Cached file is smaller than expected ({cache_size} bytes). Re-downloading..."
                    )
            except Exception as e:
                logger.warning(f"[Kaggle] Error validating local cache ({e}). Re-downloading...")

        # 3. Automatic Acquisition from Free Public Mirror
        logger.info(f"[Kaggle] Automatically downloading public dataset from {self.public_url}...")
        download_err = None

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                res = client.get(self.public_url)
                if res.status_code == 200:
                    raw_content = res.content
                    # Validate downloaded content
                    self._validate_raw_download(raw_content)

                    # Persist valid dataset to local cache
                    self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.cache_file, "wb") as f:
                        f.write(raw_content)

                    logger.info(f"[Kaggle] Acquired and cached {len(raw_content):,} bytes to {self.cache_file}")

                    records, detected_cols = self._parse_and_validate_file(self.cache_file, limit=limit)
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                    return AcquisitionSummary(
                        source=self.source_name,
                        record_count=len(records),
                        status="SUCCESS_LIVE",
                        is_fallback=False,
                        error_message=None,
                        duration_ms=duration_ms,
                        query_used=self.DATASET_NAME,
                        acquired_at=utc_now(),
                        records=records
                    )
                else:
                    download_err = f"HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            download_err = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[Kaggle] Download failed: {download_err}")

        # Failure without fabrication
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return AcquisitionSummary(
            source=self.source_name,
            record_count=0,
            status="ERROR",
            is_fallback=False,
            error_message=f"Kaggle public dataset download failed: {download_err}",
            duration_ms=duration_ms,
            query_used=self.DATASET_NAME,
            acquired_at=utc_now(),
            records=[]
        )

    def _validate_raw_download(self, content: bytes) -> None:
        """Validates payload size and content to ensure valid CSV and not an HTML error page."""
        if not content or len(content) < 1000:
            raise CorruptedDatasetError(
                f"Downloaded dataset payload is too small ({len(content)} bytes). Expected >= 1000 bytes."
            )

        # Check for HTML error response (e.g. 404/502 returned as 200 OK)
        head = content[:300].decode("utf-8", errors="replace").lower()
        if "<!doctype html" in head or "<html" in head:
            raise CorruptedDatasetError("Downloaded file is HTML error page, not a CSV dataset.")

    def _parse_and_validate_file(
        self,
        file_path: Path,
        limit: int
    ) -> Tuple[List[NewsDocument], Dict[str, Any]]:
        """Parses CSV, dynamically identifies columns, validates schema, and maps to NewsDocument."""
        records: List[NewsDocument] = []
        detected_columns: Dict[str, Any] = {}

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            row_idx = 0
            
            for row in reader:
                if not row or all(c.strip() == "" for c in row):
                    continue

                # Identify format
                # Financial PhraseBank format: col 0 = sentiment ('neutral', 'positive', 'negative'), col 1 = headline text
                if len(row) >= 2:
                    first_col = row[0].strip().lower()
                    if first_col in ("positive", "negative", "neutral"):
                        sentiment_label = first_col
                        headline = row[1].strip()
                        detected_columns = {"sentiment_col": 0, "headline_col": 1, "format": "PhraseBank-Standard"}
                    else:
                        headline = row[0].strip()
                        sentiment_label = "unlabeled"
                        detected_columns = {"headline_col": 0, "sentiment_col": None, "format": "Text-Only"}
                else:
                    headline = row[0].strip()
                    sentiment_label = "unlabeled"
                    detected_columns = {"headline_col": 0, "sentiment_col": None, "format": "Single-Column"}

                # Skip header rows
                if headline.lower() in ("headline", "title", "text", "sentence", "news"):
                    continue

                if len(headline) < 5:
                    continue

                art_id = hashlib.sha256(f"Kaggle_{headline}_{row_idx}".encode("utf-8")).hexdigest()

                # Preserve ground truth accurately; report missing labels explicitly without fake ground truth
                has_ground_truth_sentiment = sentiment_label in ("positive", "negative", "neutral")

                doc = NewsDocument(
                    id=art_id,
                    title=headline,
                    url=f"https://www.kaggle.com/datasets/takala/financial-phrasebank#row-{row_idx}",
                    source="Kaggle",
                    domain="kaggle.com",
                    published_at=utc_now(),
                    retrieved_at=utc_now(),
                    raw_text=headline,
                    query_used=self.DATASET_NAME,
                    language="English",
                    metadata={
                        "ground_truth_sentiment": sentiment_label if has_ground_truth_sentiment else None,
                        "has_ground_truth_sentiment": has_ground_truth_sentiment,
                        "ground_truth_event": None,          # Explicit: dataset has no event classification
                        "has_ground_truth_event": False,     # Explicit report: no fake event labels
                        "ground_truth_impact_score": None,   # Explicit: dataset has no impact score
                        "has_ground_truth_impact": False,
                        "dataset_name": self.DATASET_NAME,
                        "row_index": row_idx,
                        "intended_use": ["sentiment_evaluation", "model_backtesting", "nlp_validation"]
                    }
                )
                records.append(doc)
                row_idx += 1
                if row_idx >= limit:
                    break

        if not records:
            raise CorruptedDatasetError("Parsed 0 valid records from CSV file.")

        return records, detected_columns
