import logging
from typing import Dict, Any
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)

class FinancialSentimentEngine:
    """Computes directional financial sentiment strictly normalized in [-1.0, +1.0]."""

    # Loughran-McDonald & Financial PhraseBank calibrated lexicon
    NEGATIVE_KEYWORDS = {
        "loss": 0.8, "losses": 0.8, "default": 0.95, "bankruptcy": 0.98, "probe": 0.7,
        "investigation": 0.75, "cut": 0.6, "cuts": 0.6, "decline": 0.65, "plunge": 0.85,
        "fall": 0.5, "drop": 0.55, "downgrade": 0.85, "deficit": 0.7, "strain": 0.65,
        "strains": 0.65, "outflow": 0.75, "outflows": 0.75, "penalty": 0.8, "fine": 0.75,
        "fined": 0.75, "fraud": 0.95, "bottleneck": 0.6, "bottlenecks": 0.6, "shutdown": 0.7,
        "slump": 0.75, "warning": 0.6, "warns": 0.6, "inflation": 0.5, "crisis": 0.9
    }

    POSITIVE_KEYWORDS = {
        "surge": 0.85, "surges": 0.85, "record": 0.75, "beat": 0.8, "beats": 0.8,
        "growth": 0.7, "profit": 0.75, "profits": 0.75, "gain": 0.65, "gains": 0.65,
        "upgrade": 0.85, "acquire": 0.65, "acquires": 0.65, "acquisition": 0.65,
        "agreement": 0.6, "rebound": 0.7, "outperform": 0.8, "expansion": 0.65,
        "dividend": 0.6, "rally": 0.75, "exceed": 0.8, "exceeds": 0.8, "bullish": 0.8
    }

    def __init__(self):
        self.use_transformers = settings.USE_LOCAL_TRANSFORMERS
        self.model = None
        self.tokenizer = None

        if self.use_transformers:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                self.tokenizer = AutoTokenizer.from_pretrained(settings.FINBERT_MODEL_NAME)
                self.model = AutoModelForSequenceClassification.from_pretrained(settings.FINBERT_MODEL_NAME)
                self.torch = torch
                logger.info("FinBERT transformer model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load local transformer ({e}). Using explainable financial sentiment kernel.")
                self.use_transformers = False

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyzes text and returns normalized sentiment score in [-1.0, +1.0]."""
        if not text or not str(text).strip():
            return {
                "score": 0.0,
                "label": "Neutral",
                "probabilities": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                "method": "Explainable-Financial-Lexicon",
                "explanation": "No text provided or text is empty; defaulted to Neutral (0.0)."
            }

        if self.use_transformers and self.model and self.tokenizer:
            try:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                outputs = self.model(**inputs)
                probs = self.torch.nn.functional.softmax(outputs.logits, dim=-1)[0].tolist()
                # FinBERT classes: [positive, negative, neutral]
                pos, neg, neu = probs[0], probs[1], probs[2]
                score = max(-1.0, min(1.0, pos - neg))
                label = "Positive" if score > 0.15 else ("Negative" if score < -0.15 else "Neutral")
                return {
                    "score": round(score, 4),
                    "label": label,
                    "probabilities": {"positive": round(pos, 4), "negative": round(neg, 4), "neutral": round(neu, 4)},
                    "method": "FinBERT-Transformer",
                    "explanation": f"FinBERT classification: Positive {round(pos, 3)}, Negative {round(neg, 3)}, Neutral {round(neu, 3)}."
                }
            except Exception as e:
                logger.warning(f"Transformer inference error ({e}). Falling back to explainable lexicon.")

        # Explainable Lexicon Formulation: S = (Pos_weight - Neg_weight) / Normalizer
        words = text.lower().split()
        matched_pos = []
        matched_neg = []
        pos_sum = 0.0
        neg_sum = 0.0

        for w in words:
            clean_w = w.strip(".,;:\"'()[]{}!?-")
            if clean_w in self.POSITIVE_KEYWORDS:
                w_val = self.POSITIVE_KEYWORDS[clean_w]
                pos_sum += w_val
                matched_pos.append(f"{clean_w} (+{w_val})")
            elif clean_w in self.NEGATIVE_KEYWORDS:
                w_val = self.NEGATIVE_KEYWORDS[clean_w]
                neg_sum += w_val
                matched_neg.append(f"{clean_w} (-{w_val})")

        total_signal = pos_sum + neg_sum
        if total_signal == 0:
            score = 0.0
            pos_p, neg_p, neu_p = 0.1, 0.1, 0.8
            explanation = "Neutral stance: No dominant financial sentiment triggers identified."
        else:
            raw_score = (pos_sum - neg_sum) / max(1.0, total_signal)
            score = max(-1.0, min(1.0, raw_score))
            if score > 0:
                pos_p = 0.5 + (score * 0.45)
                neg_p = 0.1
                neu_p = 1.0 - pos_p - neg_p
            elif score < 0:
                neg_p = 0.5 + (abs(score) * 0.45)
                pos_p = 0.1
                neu_p = 1.0 - pos_p - neg_p
            else:
                pos_p, neg_p, neu_p = 0.15, 0.15, 0.70

            pos_desc = ", ".join(matched_pos) if matched_pos else "none"
            neg_desc = ", ".join(matched_neg) if matched_neg else "none"
            explanation = (
                f"Calibrated lexicon sentiment: Positive cues [{pos_desc}] (sum {round(pos_sum, 2)}) vs. "
                f"Negative cues [{neg_desc}] (sum {round(neg_sum, 2)}). Net score: {round(score, 3)}."
            )

        label = "Positive" if score > 0.15 else ("Negative" if score < -0.15 else "Neutral")

        return {
            "score": round(score, 4),
            "label": label,
            "probabilities": {
                "positive": round(pos_p, 4),
                "negative": round(neg_p, 4),
                "neutral": round(neu_p, 4)
            },
            "method": "Explainable-Financial-Lexicon",
            "explanation": explanation
        }
