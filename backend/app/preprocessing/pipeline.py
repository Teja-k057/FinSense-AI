import re
import html
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

from backend.app.ingestion.models import NewsDocument, AcquisitionSummary
from backend.app.preprocessing.text_cleaner import TextCleaner
from backend.app.preprocessing.entity_resolver import EntityResolver
from backend.app.ingestion.adapters.gdelt_adapter import GDELTNewsAdapter
from backend.app.ingestion.adapters.kaggle_adapter import KaggleNewsAdapter

logger = logging.getLogger("preprocessing.pipeline")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class CommonNewsPipeline:
    """
    Unified ingestion and preprocessing pipeline combining GDELT and Kaggle Financial News.
    Produces identical, canonical NewsDocument schemas for downstream NLP Risk Engine processing.
    
    Stages:
    1. Text Cleaning & HTML/Noise Removal
    2. Missing-Value Handling & Graceful Fallbacks
    3. Timestamp Normalization (various formats -> UTC datetime)
    4. Language & Content Quality Filtering
    5. Company & Entity Extraction Preparation
    6. Deduplication & Source Tracking
    """

    MIN_TEXT_LENGTH = 10
    MAX_TEXT_LENGTH = 10_000

    def __init__(self):
        self.gdelt_adapter = GDELTNewsAdapter()
        self.kaggle_adapter = KaggleNewsAdapter()
        self.seen_hashes: Set[str] = set()

    def clear_seen_cache(self) -> None:
        """Clears in-memory deduplication set."""
        self.seen_hashes.clear()

    # ================= 1. Text Cleaning & HTML/Noise Removal =================
    @classmethod
    def clean_text(cls, raw_text: Optional[str]) -> str:
        """Sanitizes text, unescapes entities, strips HTML/URLs, and expands financial acronyms."""
        if not raw_text or not isinstance(raw_text, str):
            return ""

        # Delegate to TextCleaner for core normalization
        cleaned = TextCleaner.clean(raw_text)

        # Remove repetitive boilerplate and trailing punctuation artifacts
        cleaned = re.sub(r"\s*--\s*$", "", cleaned)
        cleaned = re.sub(r"^(photo|lead|report)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    # ================= 2. Timestamp Normalization =================
    @classmethod
    def normalize_timestamp(cls, raw_ts: Any) -> datetime:
        """
        Converts diverse timestamp inputs (ISO strings, 14-digit GDELT, epoch, datetime)
        to a standard timezone-aware UTC datetime.
        """
        if isinstance(raw_ts, datetime):
            return raw_ts if raw_ts.tzinfo is not None else raw_ts.replace(tzinfo=timezone.utc)

        if not raw_ts or not isinstance(raw_ts, (str, int, float)):
            return utc_now()

        str_ts = str(raw_ts).strip()

        # Format: 14-digit GDELT seendate (e.g. '20240315123045' or '20240315T123045Z')
        clean_numeric = str_ts.replace("T", "").replace("Z", "").replace("-", "").replace(":", "").replace(" ", "")
        if len(clean_numeric) >= 14 and clean_numeric[:14].isdigit():
            try:
                return datetime.strptime(clean_numeric[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        elif len(clean_numeric) == 8 and clean_numeric.isdigit():
            try:
                return datetime.strptime(clean_numeric, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        # Format: Standard ISO-8601 string
        try:
            parsed = datetime.fromisoformat(str_ts.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass

        return utc_now()

    # ================= 3. Content Quality & Language Validation =================
    @classmethod
    def is_valid_quality(cls, title: str, text: str) -> bool:
        """Validates that document contains sufficient informative content and is not spam."""
        combined = f"{title} {text}".strip()
        if len(combined) < cls.MIN_TEXT_LENGTH:
            return False

        # Reject pure numeric or punctuation gibberish
        alphanumeric_count = sum(1 for c in combined if c.isalnum())
        if alphanumeric_count < 6:
            return False

        # Check for navigation or placeholder noise
        noise_patterns = [
            r"^404 not found",
            r"^page not found",
            r"^access denied",
            r"^enable javascript",
            r"^subscribe to read full story"
        ]
        for pattern in noise_patterns:
            if re.search(pattern, combined.lower()):
                return False

        return True

    # ================= 4. Document Normalization Kernel =================
    def process_raw_item(
        self,
        raw_item: Dict[str, Any],
        source: str
    ) -> Optional[NewsDocument]:
        """
        Normalizes an arbitrary raw item from GDELT or Kaggle into a canonical NewsDocument.
        Returns None if document fails quality checks or is an exact duplicate.
        """
        # Extract title and text
        raw_title = raw_item.get("title") or raw_item.get("headline") or ""
        raw_text = raw_item.get("text") or raw_item.get("content") or raw_title

        clean_title = self.clean_text(str(raw_title))
        clean_text_body = self.clean_text(str(raw_text))

        # Quality check
        if not self.is_valid_quality(clean_title, clean_text_body):
            logger.debug(f"[{source}] Dropping low quality item: '{clean_title[:30]}'")
            return None

        # Missing-value handling
        url = raw_item.get("url")
        if url:
            url = str(url).strip() or None

        domain = raw_item.get("domain") or (raw_item.get("metadata", {}).get("domain") if isinstance(raw_item.get("metadata"), dict) else None) or "Unknown"

        # Timestamp normalization
        raw_time = (
            raw_item.get("publication_time")
            or raw_item.get("published_at")
            or raw_item.get("seendate")
            or raw_item.get("date")
        )
        pub_time = self.normalize_timestamp(raw_time)
        ret_time = self.normalize_timestamp(raw_item.get("retrieved_time") or raw_item.get("acquired_at"))

        # Deterministic deduplication hash
        hash_seed = f"{source}_{url.lower() if url else ''}_{clean_title.lower()}"
        doc_id = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

        if doc_id in self.seen_hashes:
            logger.debug(f"[{source}] Dropping duplicate document: {doc_id[:8]}")
            return None

        self.seen_hashes.add(doc_id)

        # Company / Entity Extraction Preparation
        found_entities = EntityResolver.extract_all_entities(f"{clean_title} {clean_text_body}")

        # Ground-truth label extraction (Kaggle Financial PhraseBank)
        orig_label = (
            raw_item.get("original_label")
            or raw_item.get("raw_sentiment_label")
            or (raw_item.get("metadata", {}).get("raw_sentiment_label") if isinstance(raw_item.get("metadata"), dict) else None)
            or (raw_item.get("metadata", {}).get("ground_truth_sentiment") if isinstance(raw_item.get("metadata"), dict) else None)
        )
        if orig_label:
            orig_label = str(orig_label).strip().lower()
            if orig_label not in ("positive", "negative", "neutral"):
                orig_label = None

        doc = NewsDocument(
            id=doc_id,
            source=source,
            title=clean_title,
            text=clean_text_body,
            url=url,
            publication_time=pub_time,
            retrieved_time=ret_time,
            company_entities=found_entities,
            original_label=orig_label,
            domain=domain,
            language=raw_item.get("language", "English"),
            metadata={
                "source_pipeline": "CommonNewsPipeline",
                "clean_text_length": len(clean_text_body),
                "has_ground_truth_label": orig_label is not None,
                "raw_metadata": raw_item.get("metadata", {})
            }
        )

        return doc

    # ================= 5. High-Level Ingestion Methods =================
    def ingest_from_gdelt(
        self,
        query: str = GDELTNewsAdapter.DEFAULT_FINANCIAL_QUERY,
        timespan: str = GDELTNewsAdapter.DEFAULT_TIMESPAN,
        limit: int = 25
    ) -> List[NewsDocument]:
        """Ingests and normalizes articles from GDELT DOC API."""
        summary = self.gdelt_adapter.fetch_news(query=query, timespan=timespan, max_records=limit)
        normalized = []
        for rec in summary.records:
            doc = self.process_raw_item(rec.model_dump(), source="GDELT")
            if doc:
                normalized.append(doc)
        logger.info(f"[Pipeline] Ingested {len(normalized)} normalized documents from GDELT.")
        return normalized

    def ingest_from_kaggle(self, limit: int = 50) -> List[NewsDocument]:
        """Ingests and normalizes records from the Kaggle Financial News dataset."""
        summary = self.kaggle_adapter.acquire(limit=limit)
        normalized = []
        for rec in summary.records:
            doc = self.process_raw_item(rec.model_dump(), source="Kaggle")
            if doc:
                normalized.append(doc)
        logger.info(f"[Pipeline] Ingested {len(normalized)} normalized documents from Kaggle.")
        return normalized

    def ingest_unified(
        self,
        gdelt_limit: int = 20,
        kaggle_limit: int = 20
    ) -> List[NewsDocument]:
        """
        Combines documents from both GDELT and Kaggle into a unified stream
        ready for the downstream AI/NLP Risk Engine.
        """
        unified: List[NewsDocument] = []
        
        # 1. GDELT documents
        gdelt_docs = self.ingest_from_gdelt(limit=gdelt_limit)
        unified.extend(gdelt_docs)

        # 2. Kaggle documents
        kaggle_docs = self.ingest_from_kaggle(limit=kaggle_limit)
        unified.extend(kaggle_docs)

        # Sort combined feed chronologically descending
        unified.sort(key=lambda d: d.publication_time, reverse=True)
        logger.info(f"[Pipeline] Total unified feed generated: {len(unified)} documents.")
        return unified
