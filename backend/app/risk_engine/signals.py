import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.preprocessing.text_cleaner import TextCleaner
from backend.app.preprocessing.entity_resolver import EntityResolver
from backend.app.nlp.sentiment import FinancialSentimentEngine
from backend.app.nlp.event_classifier import FinancialEventClassifier
from backend.app.nlp.impact_scorer import FinancialImpactScorer
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.ingestion.models import NewsDocument
from backend.app.database.models import Article, RiskSignal as DBRiskSignal

logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RiskSignalEngine:
    """
    Core AI/NLP Risk Engine transforming unstructured financial news text and canonical
    NewsDocuments into structured, explainable RiskSignal objects.
    """

    def __init__(self):
        self.sentiment_engine = FinancialSentimentEngine()
        self.event_classifier = FinancialEventClassifier()
        # In-memory tracking for duplicate event detection: (company, event_type, rounded_sentiment, rounded_impact)
        self.seen_event_signatures: Set[str] = set()

    def reset_duplicate_cache(self) -> None:
        """Clears the duplicate event cache."""
        self.seen_event_signatures.clear()

    def process_text(
        self,
        raw_text: Optional[str],
        source: str = "AdHoc",
        ticker_hint: Optional[str] = None,
        article_id: Optional[str] = None,
        db: Optional[Session] = None,
        check_duplicate: bool = True
    ) -> RiskSignal:
        """
        Processes single text string, extracting entities, sentiment, event type,
        and explainable impact score into a canonical RiskSignal.
        """
        # 1. Handle Missing / Empty Text
        if not raw_text or not str(raw_text).strip():
            logger.warning("[RiskSignalEngine] Empty or missing text provided. Generating neutral baseline signal.")
            return RiskSignal(
                company=ticker_hint or "GENERAL",
                event_type="Other",
                sentiment_score=0.0,
                impact_score=1.0,
                risk_level="LOW",
                explanation="No input text provided; defaulted to neutral baseline signal.",
                source=source,
                timestamp=utc_now(),
                document_id=article_id,
                ticker=ticker_hint or "GENERAL",
                company_name="General Market",
                sentiment_label="Neutral",
                confidence=0.0,
                is_duplicate=False
            )

        # 2. Text Cleaning
        cleaned = TextCleaner.clean(raw_text)
        if len(cleaned.strip()) < 5:
            return RiskSignal(
                company=ticker_hint or "GENERAL",
                event_type="Other",
                sentiment_score=0.0,
                impact_score=1.0,
                risk_level="LOW",
                explanation=f"Text too short after cleaning ({len(cleaned)} chars); defaulted to baseline signal.",
                source=source,
                timestamp=utc_now(),
                document_id=article_id,
                ticker=ticker_hint or "GENERAL",
                company_name="General Market",
                sentiment_label="Neutral",
                confidence=0.0,
                is_duplicate=False
            )

        # 3. Entity Extraction & Resolution
        entity = EntityResolver.resolve(cleaned, ticker_hint=ticker_hint)
        resolved_ticker = entity["ticker"]
        company_name = entity["company_name"]
        sector = entity.get("sector", "General")

        # 4. Directional Sentiment Analysis [-1.0, +1.0]
        sentiment_res = self.sentiment_engine.analyze(cleaned)
        sentiment_score = sentiment_res["score"]
        sentiment_label = sentiment_res["label"]

        # 5. Event Classification (Controlled 10-Class Taxonomy)
        event_res = self.event_classifier.classify(cleaned)
        event_type = event_res["event_type"]
        event_conf = event_res["confidence"]
        event_sev_weight = event_res["severity_weight"]

        # 6. Explainable Impact Scoring [1.0, 10.0]
        in_title = bool(ticker_hint or resolved_ticker in cleaned[:100].upper())
        impact_res = FinancialImpactScorer.calculate(
            sentiment_score=sentiment_score,
            event_severity_weight=event_sev_weight,
            ticker=resolved_ticker,
            event_type=event_type,
            source=source,
            in_title=in_title
        )
        impact_score = impact_res["impact_score"]
        risk_level = impact_res["risk_level"]

        # 7. Comprehensive Reasoning Narrative
        composite_explanation = (
            f"Signal for {resolved_ticker} ({company_name}, Sector: {sector}). "
            f"Event: {event_type} (conf {event_conf:.2f}). {event_res['explanation']} "
            f"Sentiment: {sentiment_label} ({sentiment_score:+.2f}). {sentiment_res.get('explanation', '')} "
            f"Impact: {impact_score}/10 [Risk: {risk_level}]. {impact_res['explanation']}"
        )

        # 8. Duplicate Event Detection
        event_sig = f"{resolved_ticker}_{event_type}_{round(sentiment_score, 1)}_{round(impact_score, 1)}"
        is_duplicate = False
        if check_duplicate:
            if event_sig in self.seen_event_signatures:
                is_duplicate = True
                logger.debug(f"[RiskSignalEngine] Detected duplicate event signature: {event_sig}")
            else:
                self.seen_event_signatures.add(event_sig)

        signal = RiskSignal(
            company=resolved_ticker,
            event_type=event_type,
            sentiment_score=sentiment_score,
            impact_score=impact_score,
            risk_level=risk_level,
            explanation=composite_explanation,
            source=source,
            timestamp=utc_now(),
            id=hashlib.sha256(f"{article_id}_{resolved_ticker}_{event_sig}".encode()).hexdigest()[:16],
            document_id=article_id,
            title=cleaned[:100],
            ticker=resolved_ticker,
            company_name=company_name,
            sector=sector,
            confidence=event_conf,
            sentiment_label=sentiment_label,
            factor_breakdown=impact_res["factor_breakdown"],
            is_duplicate=is_duplicate
        )

        # 9. Persistence to Database if session provided
        if db:
            self._persist_to_db(signal, db)

        return signal

    def process_document(
        self,
        doc: NewsDocument,
        db: Optional[Session] = None,
        check_duplicate: bool = True
    ) -> List[RiskSignal]:
        """
        Processes a canonical NewsDocument (from GDELT or Kaggle), creating structured
        RiskSignal objects for each company entity detected.
        """
        content_to_analyze = f"{doc.title}. {doc.text}" if doc.title != doc.text else doc.title
        entities = doc.company_entities or []

        # If no explicit entities listed, resolve from text
        if not entities:
            resolved = EntityResolver.resolve(content_to_analyze)
            entities = [resolved["ticker"]]

        signals: List[RiskSignal] = []
        for ticker in entities:
            sig = self.process_text(
                raw_text=content_to_analyze,
                source=doc.source,
                ticker_hint=ticker,
                article_id=doc.id,
                db=db,
                check_duplicate=check_duplicate
            )
            # Override timestamp with publication time from document
            sig.timestamp = doc.publication_time
            signals.append(sig)

        return signals

    def process_batch(
        self,
        documents: List[NewsDocument],
        db: Optional[Session] = None,
        skip_duplicates: bool = True
    ) -> List[RiskSignal]:
        """Processes a batch of canonical NewsDocuments and returns risk signals."""
        all_signals: List[RiskSignal] = []
        for doc in documents:
            doc_signals = self.process_document(doc, db=db, check_duplicate=True)
            for s in doc_signals:
                if skip_duplicates and s.is_duplicate:
                    continue
                all_signals.append(s)
        return all_signals

    def _persist_to_db(self, signal: RiskSignal, db: Session) -> None:
        """Persists risk signal record into relational DB."""
        try:
            db_signal = DBRiskSignal(
                document_id=signal.document_id,
                article_id=signal.document_id,
                company=signal.company,
                ticker=signal.company,
                company_name=signal.company_name or signal.company,
                sector=getattr(signal, "sector", None) or "General",
                sentiment_score=signal.sentiment_score,
                sentiment_label=signal.sentiment_label or "Neutral",
                event_type=signal.event_type,
                event_confidence=signal.confidence,
                impact_score=signal.impact_score,
                risk_level=getattr(signal, "risk_level", "MEDIUM"),
                explanation=signal.explanation[:500] if signal.explanation else None,
                summary=signal.explanation[:500] if signal.explanation else None,
                source=getattr(signal, "source", "GDELT") or "GDELT"
            )
            db.add(db_signal)
            db.commit()
            db.refresh(db_signal)
        except Exception as e:
            db.rollback()
            logger.error(f"[RiskSignalEngine] Failed persisting risk signal to DB: {e}")
