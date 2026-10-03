import re
from typing import Dict, Any, Optional, List

class EntityResolver:
    """Resolves corporate mentions, aliases, and macroeconomic proxies to tickers."""

    ENTITY_MAP = {
        # Financials / Banking
        "jpmorgan": ("JPM", "JPMorgan Chase & Co.", "Financials"),
        "jpm": ("JPM", "JPMorgan Chase & Co.", "Financials"),
        "chase": ("JPM", "JPMorgan Chase & Co.", "Financials"),
        "bank of america": ("BAC", "Bank of America Corp.", "Financials"),
        "bofa": ("BAC", "Bank of America Corp.", "Financials"),
        "wells fargo": ("WFC", "Wells Fargo & Co.", "Financials"),
        "citigroup": ("C", "Citigroup Inc.", "Financials"),
        "goldman sachs": ("GS", "Goldman Sachs Group Inc.", "Financials"),
        "morgan stanley": ("MS", "Morgan Stanley", "Financials"),
        "silicon valley bank": ("SIVBQ", "Silicon Valley Bank", "Financials"),
        "svb": ("SIVBQ", "Silicon Valley Bank", "Financials"),
        "regional bank": ("KRE", "SPDR S&P Regional Banking ETF", "Financials"),
        
        # Technology / Digital Growth
        "apple": ("AAPL", "Apple Inc.", "Technology"),
        "aapl": ("AAPL", "Apple Inc.", "Technology"),
        "microsoft": ("MSFT", "Microsoft Corp.", "Technology"),
        "msft": ("MSFT", "Microsoft Corp.", "Technology"),
        "nvidia": ("NVDA", "NVIDIA Corp.", "Technology"),
        "nvda": ("NVDA", "NVIDIA Corp.", "Technology"),
        "alphabet": ("GOOGL", "Alphabet Inc.", "Technology"),
        "google": ("GOOGL", "Alphabet Inc.", "Technology"),
        "amazon": ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
        "meta": ("META", "Meta Platforms Inc.", "Technology"),
        "tesla": ("TSLA", "Tesla Inc.", "Consumer Discretionary"),
        
        # Healthcare & Pharmaceuticals
        "pfizer": ("PFE", "Pfizer Inc.", "Healthcare"),
        "johnson & johnson": ("JNJ", "Johnson & Johnson", "Healthcare"),
        "jnj": ("JNJ", "Johnson & Johnson", "Healthcare"),
        "unitedhealth": ("UNH", "UnitedHealth Group Inc.", "Healthcare"),
        "united health": ("UNH", "UnitedHealth Group Inc.", "Healthcare"),
        "unh": ("UNH", "UnitedHealth Group Inc.", "Healthcare"),
        
        # Energy Infrastructure
        "exxon": ("XOM", "Exxon Mobil Corp.", "Energy"),
        "exxonmobil": ("XOM", "Exxon Mobil Corp.", "Energy"),
        "chevron": ("CVX", "Chevron Corp.", "Energy"),
        
        # Industrial & Aerospace
        "boeing": ("BA", "Boeing Co.", "Industrials"),
        
        # Macro proxies
        "federal reserve": ("SPY", "Federal Reserve / S&P 500 Proxy", "Macro"),
        "fed": ("SPY", "Federal Reserve / S&P 500 Proxy", "Macro"),
        "interest rate": ("SPY", "Macro Interest Rate Proxy", "Macro"),
    }

    @classmethod
    def resolve(cls, text: str, ticker_hint: Optional[str] = None) -> Dict[str, Any]:
        text_lower = text.lower()

        # If explicit ticker hint is provided and valid
        if ticker_hint:
            ticker_hint_clean = ticker_hint.upper().strip()
            for k, (t, name, sec) in cls.ENTITY_MAP.items():
                if t == ticker_hint_clean:
                    return {"ticker": t, "company_name": name, "sector": sec, "confidence": 0.98}
            return {"ticker": ticker_hint_clean, "company_name": ticker_hint_clean, "sector": "General", "confidence": 0.90}

        # Check matched aliases in order of longest match first
        for keyword in sorted(cls.ENTITY_MAP.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                ticker, name, sector = cls.ENTITY_MAP[keyword]
                return {
                    "ticker": ticker,
                    "company_name": name,
                    "sector": sector,
                    "confidence": 0.95
                }

        # General market default
        return {
            "ticker": "SPY",
            "company_name": "Broad Market Index (S&P 500)",
            "sector": "Broad Market",
            "confidence": 0.70
        }

    @classmethod
    def extract_all_entities(cls, text: str) -> List[str]:
        """Extracts unique ticker candidate entities mentioned in the text."""
        text_lower = text.lower()
        found_tickers = set()

        for keyword in sorted(cls.ENTITY_MAP.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                ticker, _, _ = cls.ENTITY_MAP[keyword]
                found_tickers.add(ticker)

        return sorted(list(found_tickers))
