from .base import BaseAdapter
from .gdelt_adapter import GDELTNewsAdapter
from .kaggle_adapter import KaggleNewsAdapter
from .yfinance_adapter import YFinanceAdapter

# Backwards compatibility alias
GDELTAdapter = GDELTNewsAdapter

__all__ = [
    "BaseAdapter",
    "GDELTNewsAdapter",
    "GDELTAdapter",
    "KaggleNewsAdapter",
    "YFinanceAdapter"
]
