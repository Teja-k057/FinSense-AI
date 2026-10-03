from .manager import DataAcquisitionManager
from .models import ArticleRecord, MarketDataQuote, AcquisitionSummary
from .adapters import GDELTAdapter, KaggleNewsAdapter, YFinanceAdapter

__all__ = [
    "DataAcquisitionManager",
    "ArticleRecord",
    "MarketDataQuote",
    "AcquisitionSummary",
    "GDELTAdapter",
    "KaggleNewsAdapter",
    "YFinanceAdapter"
]
