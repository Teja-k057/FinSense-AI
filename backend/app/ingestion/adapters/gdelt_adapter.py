import json
import hashlib
import html
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set, Dict, Any
import httpx

from backend.app.config.settings import settings
from backend.app.ingestion.adapters.base import BaseAdapter
from backend.app.ingestion.models import NewsDocument, AcquisitionSummary

logger = logging.getLogger("ingestion.gdelt")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class GDELTNewsAdapter(BaseAdapter):
    """
    Production-grade adapter for the GDELT 2.0 DOC API.
    Retrieves live near-real-time financial and corporate news events.
    Enforces deduplication, schema validation, timeout/retry policies,
    and guarantees zero fabricated records.
    """

    DEFAULT_FINANCIAL_QUERY = "stocks OR earnings OR banking OR interest rate OR inflation"
    DEFAULT_TIMESPAN = "24h"
    MAX_RECORDS_LIMIT = 250

    def __init__(
        self,
        api_base: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        super().__init__("GDELT")
        self.api_base = api_base or settings.GDELT_API_BASE
        self.timeout_sec = timeout_seconds or settings.GDELT_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GDELT_MAX_RETRIES
        self.seen_article_ids: Set[str] = set()

    def clear_seen_cache(self) -> None:
        """Clears in-memory deduplication set."""
        self.seen_article_ids.clear()

    def acquire(self, **kwargs) -> AcquisitionSummary:
        """BaseAdapter interface implementation."""
        query = kwargs.get("query", self.DEFAULT_FINANCIAL_QUERY)
        timespan = kwargs.get("timespan", self.DEFAULT_TIMESPAN)
        max_records = kwargs.get("max_records", 25)
        return self.fetch_news(query=query, timespan=timespan, max_records=max_records)

    def fetch_news(
        self,
        query: str = DEFAULT_FINANCIAL_QUERY,
        timespan: str = DEFAULT_TIMESPAN,
        max_records: int = 50
    ) -> AcquisitionSummary:
        """
        Primary service method called by the ingestion pipeline.
        
        Args:
            query: Financial search keywords
            timespan: GDELT timespan string (e.g. '15m', '1h', '6h', '24h', '7d')
            max_records: Maximum articles to fetch (clamped 1-250)
            
        Returns:
            AcquisitionSummary containing normalized NewsDocument records.
        """
        start_time = time.perf_counter()
        clamped_max = max(1, min(self.MAX_RECORDS_LIMIT, max_records))
        full_query = f"({query}) sourcelang:english"

        params = {
            "query": full_query,
            "mode": "artlist",
            "maxrecords": str(clamped_max),
            "timespan": timespan,
            "format": "json",
            "sort": "datedesc"
        }

        headers = {
            "User-Agent": "CRISIL-RiskEngine/1.0 (+http://localhost:8000)",
            "Accept": "application/json"
        }

        logger.info(
            f"[GDELT] Initiating query: '{query}' | Timespan: {timespan} | Max: {clamped_max} records"
        )

        last_error: Optional[str] = None
        raw_articles: List[Dict[str, Any]] = []

        # Execute request with configurable retries and exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"[GDELT] HTTP GET {self.api_base} (Attempt {attempt}/{self.max_retries})")
                with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                    response = client.get(self.api_base, params=params, headers=headers)

                    if response.status_code == 200:
                        raw_articles, parse_err = self._safe_parse_json(response.text)
                        if parse_err:
                            last_error = parse_err
                            logger.warning(f"[GDELT] Attempt {attempt} JSON validation failed: {parse_err}")
                        else:
                            # Success
                            last_error = None
                            break
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        logger.warning(f"[GDELT] Attempt {attempt} failed with status {response.status_code}")

            except httpx.TimeoutException as te:
                last_error = f"TimeoutException: Handshake or read timed out after {self.timeout_sec}s ({te})"
                logger.warning(f"[GDELT] Attempt {attempt} timed out: {last_error}")
            except httpx.RequestError as re:
                last_error = f"RequestError: Network or connection failure ({re})"
                logger.warning(f"[GDELT] Attempt {attempt} network error: {last_error}")
            except Exception as e:
                last_error = f"UnexpectedException ({type(e).__name__}): {e}"
                logger.error(f"[GDELT] Attempt {attempt} unexpected error: {last_error}", exc_info=True)

            if attempt < self.max_retries:
                backoff_sleep = 0.5 * (2 ** (attempt - 1))
                time.sleep(backoff_sleep)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Handle failure: NEVER FABRICATE DATA
        if last_error is not None:
            logger.error(
                f"[GDELT] Ingestion failed after {self.max_retries} attempts in {duration_ms}ms. "
                f"Error: {last_error}. Returning empty record set."
            )
            return AcquisitionSummary(
                source="GDELT",
                record_count=0,
                status="ERROR",
                is_fallback=False,
                error_message=last_error,
                duration_ms=duration_ms,
                query_used=query,
                acquired_at=utc_now(),
                records=[]
            )

        # Normalize and deduplicate articles
        normalized_records = self._normalize_articles(raw_articles, query_used=query)
        status = "SUCCESS_LIVE" if normalized_records else "EMPTY"

        logger.info(
            f"[GDELT] Completed in {duration_ms}ms. "
            f"Raw: {len(raw_articles)} | Normalized & Unique: {len(normalized_records)}"
        )

        return AcquisitionSummary(
            source="GDELT",
            record_count=len(normalized_records),
            status=status,
            is_fallback=False,
            error_message=None,
            duration_ms=duration_ms,
            query_used=query,
            acquired_at=utc_now(),
            records=normalized_records
        )

    def _safe_parse_json(self, raw_text: str) -> (List[Dict[str, Any]], Optional[str]):
        """Safely parses and validates GDELT JSON response structure."""
        if not raw_text or not raw_text.strip():
            return [], "Empty response body"

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as jde:
            snippet = raw_text[:120].replace("\n", " ")
            return [], f"Invalid JSON payload: {jde} (Snippet: {snippet})"

        if not isinstance(data, dict):
            return [], f"Expected JSON object, got {type(data).__name__}"

        articles = data.get("articles")
        if articles is None:
            # GDELT sometimes returns {"articles": []} or empty message
            return [], None

        if not isinstance(articles, list):
            return [], f"Malformed 'articles' field: expected list, got {type(articles).__name__}"

        return articles, None

    def _normalize_articles(
        self,
        raw_articles: List[Dict[str, Any]],
        query_used: str
    ) -> List[NewsDocument]:
        """Validates fields, unescapes text, deduplicates, and produces NewsDocument instances."""
        normalized: List[NewsDocument] = []

        for item in raw_articles:
            if not isinstance(item, dict):
                continue

            raw_title = item.get("title")
            if not raw_title or not isinstance(raw_title, str):
                continue

            title = html.unescape(raw_title.strip())
            # Skip invalid, truncated or trivial titles
            if len(title) < 5:
                continue

            url = (item.get("url") or "").strip()
            domain = (item.get("domain") or "").strip() or "Unknown"

            # Parse GDELT seendate (e.g. '20240315T120000Z' or '20240315120000')
            seendate = str(item.get("seendate") or "").strip()
            published_at = self._parse_gdelt_timestamp(seendate)

            # Compute deterministic ID based on canonical URL and title
            id_source = f"{url.lower()}_{title.lower()}" if url else f"gdelt_{title.lower()}_{seendate}"
            art_id = hashlib.sha256(id_source.encode("utf-8")).hexdigest()

            # Deduplication: avoid duplicates within batch or across current session
            if art_id in self.seen_article_ids:
                logger.debug(f"[GDELT] Skipping duplicate article: '{title[:40]}...' (ID: {art_id[:8]})")
                continue

            self.seen_article_ids.add(art_id)

            doc = NewsDocument(
                id=art_id,
                title=title,
                url=url if url else None,
                source="GDELT",
                domain=domain,
                published_at=published_at,
                retrieved_at=utc_now(),
                raw_text=title,
                query_used=query_used,
                language=item.get("language", "English"),
                metadata={
                    "raw_seendate": seendate,
                    "source_country": item.get("sourcecountry"),
                    "social_image": item.get("socialimage")
                }
            )
            normalized.append(doc)

        return normalized

    @staticmethod
    def _parse_gdelt_timestamp(seendate: str) -> datetime:
        """Parses variable GDELT timestamp formats to UTC datetime."""
        clean = seendate.replace("T", "").replace("Z", "")
        if len(clean) >= 14:
            try:
                return datetime.strptime(clean[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        elif len(clean) >= 8:
            try:
                return datetime.strptime(clean[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return utc_now()

# Backwards compatibility alias
GDELTAdapter = GDELTNewsAdapter
