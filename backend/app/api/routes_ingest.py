from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional

from backend.app.schemas.common import APIResponse
from backend.app.ingestion.manager import DataAcquisitionManager
from backend.app.ingestion.models import AcquisitionSummary, NewsDocument
from backend.app.preprocessing.pipeline import CommonNewsPipeline

router = APIRouter(prefix="/ingest")
acquisition_manager = DataAcquisitionManager()
unified_pipeline = CommonNewsPipeline()

@router.get("/status", response_model=APIResponse[Dict[str, Any]])
def get_adapters_status():
    """Returns connectivity, seen records count, and cache status across all data source adapters."""
    status_info = acquisition_manager.get_source_health()
    return APIResponse(status="success", data=status_info)

@router.post("/gdelt", response_model=APIResponse[AcquisitionSummary])
def ingest_gdelt(
    query: str = Query("stocks OR earnings OR banking OR interest rate", description="Search query keywords"),
    timespan: str = Query("24h", description="GDELT timespan window (e.g. 15m, 1h, 6h, 24h, 7d)"),
    limit: int = Query(25, ge=1, le=250, description="Maximum articles to fetch")
):
    """
    Automatically queries GDELT 2.0 DOC API with configurable query,
    timespan, deduplication, retry policy, and validation.
    Never fabricates GDELT records.
    """
    summary = acquisition_manager.acquire_gdelt(
        query=query,
        timespan=timespan,
        max_records=limit
    )
    return APIResponse(status="success", data=summary)

@router.post("/kaggle", response_model=APIResponse[AcquisitionSummary])
def ingest_kaggle(
    limit: int = Query(25, ge=1, le=100),
    force_download: bool = Query(False, description="Force re-download from public source")
):
    """Automatically acquires, caches, and parses public Kaggle Financial News dataset."""
    summary = acquisition_manager.acquire_kaggle(limit=limit, force_download=force_download)
    return APIResponse(status="success", data=summary)

@router.post("/unified", response_model=APIResponse[List[NewsDocument]])
def ingest_unified_news(
    gdelt_limit: int = Query(15, ge=1, le=100),
    kaggle_limit: int = Query(15, ge=1, le=100)
):
    """
    Unified Ingestion Endpoint:
    Combines GDELT and Kaggle Financial News into a single, canonical NewsDocument feed
    preprocessed and ready for downstream NLP Risk Engine evaluation.
    """
    documents = unified_pipeline.ingest_unified(
        gdelt_limit=gdelt_limit,
        kaggle_limit=kaggle_limit
    )
    return APIResponse(status="success", data=documents)

@router.get("/market-data", response_model=APIResponse[AcquisitionSummary])
def ingest_market_data(
    tickers: Optional[str] = Query(None, description="Comma-separated tickers. Defaults to 15-stock mock index."),
    force_refresh: bool = Query(False)
):
    """Automatically retrieves market prices and stats for index constituents via yfinance."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else None
    summary = acquisition_manager.acquire_market_data(tickers=ticker_list, force_refresh=force_refresh)
    return APIResponse(status="success", data=summary)
