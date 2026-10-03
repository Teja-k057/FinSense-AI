from typing import Dict, Any

class ScenarioRegistry:
    """Pre-calibrated historical crisis scenarios and macroeconomic stress vectors."""

    SCENARIOS = {
        "HISTORICAL_2008": {
            "name": "2008 Lehman Liquidity Shock",
            "description": "Systemic banking crisis with freeze in short-term wholesale funding and broad market liquidation.",
            "direct_shocks": {
                "JPM": -0.28, "BAC": -0.36, "C": -0.45, "GS": -0.25,
                "AAPL": -0.15, "NVDA": -0.22, "XOM": -0.18, "JNJ": -0.08, "SPY": -0.20
            },
            "volatility_multiplier": 2.2,
            "macro_rate_shift_bps": -150
        },
        "COVID_2020": {
            "name": "2020 COVID-19 Liquidity & Demand Crash",
            "description": "Global economic shutdown shock across energy, transport, and cyclical assets.",
            "direct_shocks": {
                "XOM": -0.38, "CVX": -0.32, "BA": -0.45, "JPM": -0.22,
                "AAPL": -0.12, "NVDA": -0.10, "JNJ": -0.05, "SPY": -0.24
            },
            "volatility_multiplier": 2.5,
            "macro_rate_shift_bps": -100
        },
        "SVB_2023": {
            "name": "2023 SVB Regional Banking Panic",
            "description": "Unrealized bond losses and rapid deposit runs triggering regional bank contagion.",
            "direct_shocks": {
                "KRE": -0.28, "JPM": -0.09, "C": -0.14, "BAC": -0.12,
                "AAPL": -0.03, "NVDA": -0.02, "XOM": -0.04, "JNJ": -0.02, "SPY": -0.06
            },
            "volatility_multiplier": 1.6,
            "macro_rate_shift_bps": 25
        }
    }

    @classmethod
    def get_scenario(cls, key: str) -> Dict[str, Any]:
        return cls.SCENARIOS.get(key, cls.SCENARIOS["HISTORICAL_2008"])
