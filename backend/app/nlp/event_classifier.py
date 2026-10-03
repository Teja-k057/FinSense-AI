import re
from typing import Dict, Any, List

class FinancialEventClassifier:
    """
    Classifies unstructured financial text into a strictly controlled 10-class risk taxonomy
    with deterministic matching and complete explainability.
    """

    CONTROLLED_TAXONOMY: List[str] = [
        "Geopolitical",
        "Macroeconomic",
        "Credit Event",
        "Merger/Acquisition",
        "Product Launch",
        "Regulatory",
        "Earnings",
        "Supply Chain",
        "Cybersecurity",
        "Other"
    ]

    TAXONOMY_RULES: Dict[str, List[str]] = {
        "Geopolitical": [
            "war", "conflict", "sanctions", "tariff", "tariffs", "trade war", "embargo",
            "military", "missile", "geopolitical", "treaty", "nato", "defense", "sovereignty",
            "invasion", "hostilities", "blockade", "weapon", "national security"
        ],
        "Macroeconomic": [
            "federal reserve", "fed", "interest rate", "rate hike", "rate cut", "inflation",
            "cpi", "gdp", "recession", "unemployment", "treasury yield", "central bank",
            "monetary policy", "stagflation", "jobs report", "ecb", "quantitative easing",
            "tightening", "bond yield", "yield curve", "macro"
        ],
        "Credit Event": [
            "default", "bankruptcy", "debt", "liquidity", "insolvency", "restructuring",
            "downgrade", "credit rating", "loan loss", "provisions", "credit default swap",
            "cds", "outflow", "deposit run", "capital shortfall", "non-performing",
            "distressed debt", "missed payment", "chapter 11", "liquidity crunch"
        ],
        "Merger/Acquisition": [
            "acquisition", "merger", "buyout", "takeover", "divestiture", "spin-off",
            "acquire", "acquires", "acquired", "tender offer", "deal", "stake", "reorganization",
            "hostile bid", "joint venture", "amalgamation"
        ],
        "Product Launch": [
            "launch", "launches", "launched", "unveil", "unveils", "unveiled", "rollout",
            "new product", "next-gen", "innovation", "release", "releases", "flagship",
            "patent", "commercial release", "service debut", "feature rollout"
        ],
        "Regulatory": [
            "sec", "investigation", "probe", "lawsuit", "penalty", "fine", "fined",
            "antitrust", "compliance", "subpoena", "fraud", "court", "ruling", "doj",
            "ftc", "settlement", "litigation", "injunction", "regulator", "sanction"
        ],
        "Earnings": [
            "earnings", "revenue", "profit", "net income", "operating income", "guidance",
            "quarterly", "margin", "ebitda", "sales", "forecast", "beat", "beats", "miss",
            "misses", "fy24", "q1", "q2", "q3", "q4", "eps", "dividend", "financial results"
        ],
        "Supply Chain": [
            "supply chain", "shortage", "bottleneck", "factory shutdown", "outage",
            "logistics", "shipping", "component", "production cap", "semiconductor shortage",
            "freight disruption", "supplier delay", "raw materials", "inventory constraint"
        ],
        "Cybersecurity": [
            "cyberattack", "data breach", "ransomware", "hack", "hacked", "hacker",
            "vulnerability", "malware", "phishing", "ddos", "security incident",
            "compromised", "zero-day", "data leak", "unauthorized access", "infosec"
        ],
        "Other": []
    }

    SEVERITY_WEIGHTS: Dict[str, float] = {
        "Credit Event": 1.00,
        "Cybersecurity": 0.90,
        "Regulatory": 0.85,
        "Geopolitical": 0.80,
        "Macroeconomic": 0.80,
        "Earnings": 0.75,
        "Supply Chain": 0.70,
        "Merger/Acquisition": 0.65,
        "Product Launch": 0.55,
        "Other": 0.40
    }

    @classmethod
    def classify(cls, text: str) -> Dict[str, Any]:
        """
        Deterministically classifies financial text into the controlled taxonomy.
        Returns explicit event_type, confidence, trigger matches, and explainability summary.
        """
        if not text or not str(text).strip():
            return {
                "event_type": "Other",
                "confidence": 0.0,
                "explanation": "No text provided; classified as 'Other'.",
                "severity_weight": cls.SEVERITY_WEIGHTS["Other"],
                "matched_keywords": []
            }

        text_lower = text.lower()
        scores: Dict[str, int] = {}
        matched_tokens: Dict[str, List[str]] = {}

        for category, keywords in cls.TAXONOMY_RULES.items():
            if not keywords:
                scores[category] = 0
                matched_tokens[category] = []
                continue

            count = 0
            hits = []
            for kw in keywords:
                # Word boundary match to avoid false positive substring matches
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, text_lower):
                    count += 1
                    hits.append(kw)
            scores[category] = count
            matched_tokens[category] = hits

        # Identify highest frequency category
        sorted_cats = sorted(
            scores.keys(),
            key=lambda c: (scores[c], cls.SEVERITY_WEIGHTS.get(c, 0.5)),
            reverse=True
        )
        best_cat = sorted_cats[0]
        best_score = scores[best_cat]

        if best_score == 0:
            best_cat = "Other"
            confidence = 0.40
            explanation = "No specific category keywords triggered; defaulted to 'Other'."
            matched_list = []
        else:
            total_hits = sum(scores.values())
            confidence = min(0.98, round(0.50 + (best_score / max(1, total_hits)) * 0.45, 2))
            matched_list = matched_tokens[best_cat]
            hits_str = ", ".join(matched_list)
            explanation = f"Classified as '{best_cat}' by matching triggers: [{hits_str}] (confidence: {confidence})."

        return {
            "event_type": best_cat,
            "confidence": confidence,
            "explanation": explanation,
            "severity_weight": cls.SEVERITY_WEIGHTS.get(best_cat, 0.50),
            "matched_keywords": matched_list
        }
