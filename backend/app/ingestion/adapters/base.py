import time
import logging
from abc import ABC, abstractmethod
from typing import Any
from backend.app.ingestion.models import AcquisitionSummary

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    """Abstract base class for all free data acquisition adapters."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(f"ingestion.{source_name.lower()}")

    @abstractmethod
    def acquire(self, **kwargs) -> AcquisitionSummary:
        """Acquires data from source, caches it, and returns normalized AcquisitionSummary."""
        pass

    def execute_with_timing(self, acquire_fn, **kwargs) -> AcquisitionSummary:
        start_time = time.perf_counter()
        try:
            summary = acquire_fn(**kwargs)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            summary.duration_ms = duration_ms
            self.logger.info(
                f"[{self.source_name}] Acquired {summary.record_count} records in {duration_ms}ms. "
                f"Status: {summary.status} (Fallback: {summary.is_fallback})"
            )
            return summary
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.error(f"[{self.source_name}] Unhandled exception during acquisition: {e}", exc_info=True)
            return AcquisitionSummary(
                source=self.source_name,
                record_count=0,
                status="ERROR",
                is_fallback=False,
                error_message=str(e),
                duration_ms=duration_ms,
                records=[]
            )
