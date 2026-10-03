import logging
from typing import Dict, Any, Optional
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)

class FinancialImpactScorer:
    """
    Calculates an explainable financial risk impact score strictly on a 1.0 to 10.0 scale.
    
    IMPORTANT NOTICE / DISCLAIMER:
    This scoring methodology is the project's explainable hackathon methodology created for
    the S&P Global × CRISIL Phase III Case Study Competition prototype. It does NOT claim to
    be, and is NOT, an official S&P Global or CRISIL rating or risk assessment methodology.
    """

    METHODOLOGY_LABEL = "Project Explainable Hackathon Methodology (Academic Prototype - Not Official S&P Global or CRISIL Methodology)"

    # Category systemic baseline risk coefficients [0.0 - 1.0]
    CATEGORY_RISK_FACTORS = {
        "Credit Event": 0.95,
        "Cybersecurity": 0.90,
        "Regulatory": 0.85,
        "Geopolitical": 0.80,
        "Macroeconomic": 0.80,
        "Supply Chain": 0.75,
        "Earnings": 0.70,
        "Merger/Acquisition": 0.65,
        "Product Launch": 0.55,
        "Other": 0.35
    }

    # SIFI & Mega-cap systemic entity weightings
    SYSTEMIC_ENTITIES = {
        "JPM": 1.25, "BAC": 1.20, "GS": 1.15, "WFC": 1.15, "MS": 1.15, "C": 1.15,
        "AAPL": 1.20, "MSFT": 1.20, "NVDA": 1.20, "GOOGL": 1.15, "AMZN": 1.15,
        "TSLA": 1.15, "XOM": 1.10, "CVX": 1.10, "JNJ": 1.05, "PFE": 1.05, "UNH": 1.10, "BA": 1.15
    }

    # Market sensitivity (annualized baseline volatility proxy)
    TICKER_VOLATILITY_PROXY = {
        "NVDA": 0.45, "TSLA": 0.48, "BA": 0.35, "AMD": 0.42, "AMZN": 0.30,
        "AAPL": 0.24, "MSFT": 0.22, "GOOGL": 0.26, "JPM": 0.22, "BAC": 0.25,
        "GS": 0.24, "XOM": 0.22, "CVX": 0.21, "JNJ": 0.16, "PFE": 0.19, "UNH": 0.18
    }

    @classmethod
    def calculate(
        cls,
        sentiment_score: float,
        event_severity_weight: float,
        ticker: str = "GENERAL",
        event_type: str = "Other",
        source: str = "GDELT",
        in_title: bool = True,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Explainable 5-factor formulation:
        Raw Impact = (
            w_severity * Event_Severity +
            w_sentiment * Sentiment_Magnitude +
            w_category * Category_Risk +
            w_entity * Entity_Relevance +
            w_market * Market_Sensitivity
        ) / Sum(Weights)
        
        Impact Score = clamp(round(1.0 + 9.0 * Raw_Impact, 1), 1.0, 10.0)
        """
        # 1. Configurable Factor Weights
        w_sev = getattr(settings, "IMPACT_WEIGHT_EVENT_SEVERITY", 0.30)
        w_sent = getattr(settings, "IMPACT_WEIGHT_SENTIMENT_MAGNITUDE", 0.25)
        w_cat = getattr(settings, "IMPACT_WEIGHT_CATEGORY_RISK", 0.20)
        w_ent = getattr(settings, "IMPACT_WEIGHT_ENTITY_RELEVANCE", 0.15)
        w_mkt = getattr(settings, "IMPACT_WEIGHT_MARKET_SENSITIVITY", 0.10)

        if custom_weights:
            w_sev = custom_weights.get("severity", w_sev)
            w_sent = custom_weights.get("sentiment", w_sent)
            w_cat = custom_weights.get("category", w_cat)
            w_ent = custom_weights.get("entity", w_ent)
            w_mkt = custom_weights.get("market", w_mkt)

        total_weight = w_sev + w_sent + w_cat + w_ent + w_mkt
        if total_weight <= 0:
            total_weight = 1.0

        # 2. Factor Quantification
        # a. Event severity [0.1 - 1.0]
        f_severity = max(0.1, min(1.0, event_severity_weight))

        # b. Sentiment magnitude [0.0 - 1.0]
        sentiment_mag = min(1.0, abs(sentiment_score))

        # c. Category systemic risk [0.1 - 1.0]
        f_category = cls.CATEGORY_RISK_FACTORS.get(event_type, 0.40)

        # d. Entity relevance [0.2 - 1.0]
        entity_mult = cls.SYSTEMIC_ENTITIES.get(ticker.upper(), 1.0)
        position_mult = 1.0 if in_title else 0.8
        f_entity = min(1.0, (entity_mult * position_mult) / 1.25)

        # e. Market sensitivity / Volatility proxy [0.1 - 1.0]
        vol = cls.TICKER_VOLATILITY_PROXY.get(ticker.upper(), 0.25)
        f_market = min(1.0, vol / 0.50)  # 50% vol maps to 1.0

        # 3. Weighted Aggregation
        raw_weighted = (
            w_sev * f_severity +
            w_sent * sentiment_mag +
            w_cat * f_category +
            w_ent * f_entity +
            w_mkt * f_market
        ) / total_weight

        # 4. Strictly clamp to [1.0, 10.0]
        scaled = 1.0 + (9.0 * raw_weighted)
        final_score = max(1.0, min(10.0, round(scaled, 1)))

        # 5. Risk Level Classification
        risk_level = cls.determine_risk_level(final_score, sentiment_score, event_type)

        # 6. Plain-English Explainability Narrative
        explanation = (
            f"Impact Score {final_score}/10 calculated via {cls.METHODOLOGY_LABEL}. "
            f"Components: Event Severity {round(f_severity, 2)} (weight {w_sev:.2f}), "
            f"Sentiment Magnitude {round(sentiment_mag, 2)} (weight {w_sent:.2f}), "
            f"Category Risk '{event_type}' {round(f_category, 2)} (weight {w_cat:.2f}), "
            f"Entity Relevance ({ticker}) {round(f_entity, 2)} (weight {w_ent:.2f}), "
            f"Market Sensitivity {round(f_market, 2)} (weight {w_mkt:.2f})."
        )

        return {
            "impact_score": final_score,
            "risk_level": risk_level,
            "factor_breakdown": {
                "event_severity": round(f_severity, 4),
                "sentiment_magnitude": round(sentiment_mag, 4),
                "category_risk": round(f_category, 4),
                "entity_relevance": round(f_entity, 4),
                "market_sensitivity": round(f_market, 4),
                "weights": {
                    "severity": w_sev,
                    "sentiment": w_sent,
                    "category": w_cat,
                    "entity": w_ent,
                    "market": w_mkt
                }
            },
            "explanation": explanation,
            "methodology": cls.METHODOLOGY_LABEL
        }

    @staticmethod
    def determine_risk_level(impact_score: float, sentiment_score: float, event_type: str) -> str:
        """Determines categorical risk level (CRITICAL, HIGH, MEDIUM, LOW)."""
        if impact_score >= 8.0 and sentiment_score <= -0.2:
            return "CRITICAL"
        if event_type in ("Credit Event", "Cybersecurity") and impact_score >= 7.5:
            return "CRITICAL"
        if impact_score >= 6.5 or (impact_score >= 5.0 and sentiment_score <= -0.3):
            return "HIGH"
        if impact_score >= 4.0:
            return "MEDIUM"
        return "LOW"
