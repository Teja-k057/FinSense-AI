import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from backend.app.rebalancer.models import (
    RebalanceAction,
    ConstituentRebalanceDetail,
    RebalanceSummary,
    RebalanceRequest
)
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.nlp.event_classifier import FinancialEventClassifier
from backend.app.portfolio.market_data import MarketDataService
from backend.app.portfolio.models import TickerMarketData

logger = logging.getLogger("rebalancer.engine")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RebalancingEngine:
    """
    MODULE A: Tactical High-Frequency Stock Index Rebalancer.
    
    Transforms AI/NLP Risk Engine signals and market data into tactical index weight tilts.
    Features:
    - 15-stock liquid mock index universe across 5 GICS sectors.
    - Fully deterministic, non-random optimization.
    - Strict constraint satisfaction (Sum = 100%, Min/Max weight bounds, Turnover limit).
    - Plain-English explainable action attribution for every constituent.
    
    DISCLAIMER:
    This algorithm is an academic hackathon simulation prototype for the S&P Global x CRISIL
    Case Study Competition. It does NOT constitute financial, investment, or trading advice.
    """

    DISCLAIMER = (
        "Tactical High-Frequency Stock Index Rebalancer Prototype "
        "(Academic Hackathon Model - Not Financial or Investment Advice)"
    )

    # 15 Liquid S&P 500 Mock Index Universe
    DEFAULT_UNIVERSE = MarketDataService.DEFAULT_INDEX_UNIVERSE

    def __init__(self, market_data_service: Optional[MarketDataService] = None):
        self.market_service = market_data_service or MarketDataService()

    # -------------------------------------------------------------------------
    # 1. calculate_signal()
    # -------------------------------------------------------------------------
    def calculate_signal(
        self,
        ticker: str,
        signals: Optional[List[RiskSignal]] = None,
        market_data: Optional[TickerMarketData] = None
    ) -> Dict[str, Any]:
        """
        Combines news sentiment, event impact, event severity, and recent market movement
        into a unified, deterministic tactical signal tilt in [-1.0, +1.0].
        """
        # A. Aggregate News Signals
        if signals and len(signals) > 0:
            # Weighted average sentiment by impact score: severe news carries heavier weight
            total_impact = sum(s.impact_score for s in signals)
            if total_impact > 0:
                avg_sentiment = sum(s.sentiment_score * s.impact_score for s in signals) / total_impact
            else:
                avg_sentiment = sum(s.sentiment_score for s in signals) / len(signals)

            avg_impact = sum(s.impact_score for s in signals) / len(signals)

            # Identify dominant event type (event with highest impact)
            sorted_signals = sorted(signals, key=lambda s: s.impact_score, reverse=True)
            dominant_event = sorted_signals[0].event_type
            severity_weight = FinancialEventClassifier.SEVERITY_WEIGHTS.get(dominant_event, 0.50)
            signal_count = len(signals)
        else:
            # Safe handling of missing signals
            avg_sentiment = 0.0
            avg_impact = 5.0
            dominant_event = "Other"
            severity_weight = FinancialEventClassifier.SEVERITY_WEIGHTS.get("Other", 0.40)
            signal_count = 0

        # Impact factor normalized to [0.0, 1.0]
        impact_factor = (avg_impact - 1.0) / 9.0

        # B. Recent Market Movement & Volatility
        recent_return = 0.0
        volatility = None
        if market_data:
            # Trailing return proxy: average of daily returns * 21 (1-month proxy) or change_pct
            if market_data.trailing_daily_returns and len(market_data.trailing_daily_returns) > 0:
                recent_return = sum(market_data.trailing_daily_returns[-20:])
            elif market_data.change_pct:
                recent_return = market_data.change_pct / 100.0
            volatility = market_data.annualized_volatility

        # Return momentum factor in [-1.0, +1.0]
        clamped_ret = max(-0.20, min(0.20, recent_return))
        ret_factor = clamped_ret / 0.20

        # C. Deterministic Signal Synthesis
        # Sentiment tilt:
        if avg_sentiment > 0.0:
            # Positive sentiment with moderate impact increases allocation
            # Excessively high impact (> 8.5) slightly moderates tilt to prevent overconcentration
            impact_dampener = 1.0 - (0.25 * max(0.0, (avg_impact - 6.0) / 4.0))
            sentiment_tilt = avg_sentiment * impact_dampener
        elif avg_sentiment < 0.0:
            # Negative sentiment is amplified by high impact and critical event severity
            severity_amplifier = 0.70 + (0.50 * impact_factor * severity_weight)
            sentiment_tilt = avg_sentiment * severity_amplifier
        else:
            sentiment_tilt = 0.0

        # Combine sentiment tilt (80%) and recent return momentum (20%)
        raw_combined = (0.80 * sentiment_tilt) + (0.20 * ret_factor)

        # Volatility penalty: if annualized vol > 35%, penalize positive tilts
        if volatility and volatility > 0.35 and raw_combined > 0:
            vol_penalty = 1.0 - min(0.30, (volatility - 0.35) * 1.5)
            raw_combined *= vol_penalty

        # Strictly clamp tactical signal to [-1.0, +1.0]
        tactical_signal = max(-1.0, min(1.0, round(raw_combined, 4)))

        return {
            "tactical_signal": tactical_signal,
            "avg_sentiment": round(avg_sentiment, 4),
            "avg_impact": round(avg_impact, 1),
            "dominant_event": dominant_event,
            "severity_weight": severity_weight,
            "recent_return": round(recent_return, 4),
            "volatility": round(volatility, 4) if volatility else None,
            "signal_count": signal_count
        }

    # -------------------------------------------------------------------------
    # 2. calculate_target_weights()
    # -------------------------------------------------------------------------
    def calculate_target_weights(
        self,
        current_weights: Dict[str, float],
        signals: Dict[str, float],
        tilt_multiplier: float = 0.60
    ) -> Dict[str, float]:
        """
        Converts tactical signals into unconstrained raw target weights.
        Positive signal increases weight above base; negative signal reduces weight below base.
        """
        raw_targets: Dict[str, float] = {}

        for ticker, base_w in current_weights.items():
            sig = signals.get(ticker, 0.0)
            # Tilt: raw_target = base_w * (1 + tilt_multiplier * signal)
            tilt_ratio = 1.0 + (tilt_multiplier * sig)
            raw_targets[ticker] = max(0.001, base_w * tilt_ratio)

        return raw_targets

    # -------------------------------------------------------------------------
    # 3. apply_constraints()
    # -------------------------------------------------------------------------
    def apply_constraints(
        self,
        raw_weights: Dict[str, float],
        min_weight: float = 0.02,
        max_weight: float = 0.15,
        max_turnover: Optional[float] = None,
        current_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Applies portfolio constraints via iterative water-filling projection:
        1. Minimum weight floor (e.g. 2.0%)
        2. Maximum weight cap (e.g. 15.0%)
        3. Total weights strictly sum to 1.0 (100.0%)
        4. Optional max turnover constraint
        """
        tickers = list(raw_weights.keys())
        n = len(tickers)
        if n == 0:
            return {}

        # Feasibility check: min_weight * n <= 1.0 and max_weight * n >= 1.0
        if min_weight * n > 1.0:
            min_weight = 1.0 / n
        if max_weight * n < 1.0:
            max_weight = 1.0 / n

        # Initial normalization
        total_raw = sum(raw_weights.values())
        if total_raw <= 0:
            weights = {t: 1.0 / n for t in tickers}
        else:
            weights = {t: raw_weights[t] / total_raw for t in tickers}

        # Iterative bounded projection (exact water-filling)
        max_iter = 50
        for _ in range(max_iter):
            # Clamp to bounds
            clamped = {}
            for t in tickers:
                clamped[t] = max(min_weight, min(max_weight, weights[t]))

            total_clamped = sum(clamped.values())
            diff = 1.0 - total_clamped

            if abs(diff) < 1e-8:
                weights = clamped
                break

            # Find assets that are free to adjust (not saturated at bounds)
            if diff > 0:  # Deficit: need to add weight
                adjustable = [t for t in tickers if clamped[t] < max_weight - 1e-8]
            else:  # Surplus: need to subtract weight
                adjustable = [t for t in tickers if clamped[t] > min_weight + 1e-8]

            if not adjustable:
                weights = clamped
                break

            # Distribute diff equally or proportionally across adjustable assets
            delta = diff / len(adjustable)
            for t in adjustable:
                clamped[t] += delta

            weights = clamped

        # Final precision normalization to ensure exact sum = 1.0
        final_sum = sum(weights.values())
        weights = {t: round(w / final_sum, 6) for t, w in weights.items()}
        # Reconcile any rounding fractional deficit on the asset furthest from bounds
        discrepancy = round(1.0 - sum(weights.values()), 6)
        if discrepancy != 0:
            best_ticker = max(tickers, key=lambda t: min(max_weight - weights[t], weights[t] - min_weight))
            weights[best_ticker] = round(weights[best_ticker] + discrepancy, 6)

        # Optional Turnover Constraint: sum(|w_target - w_current|) / 2 <= max_turnover
        if max_turnover is not None and current_weights is not None:
            weights = self._apply_turnover_limit(weights, current_weights, max_turnover)

        return weights

    def _apply_turnover_limit(
        self,
        target_weights: Dict[str, float],
        current_weights: Dict[str, float],
        max_turnover: float
    ) -> Dict[str, float]:
        """Clamps overall portfolio turnover to max_turnover threshold."""
        raw_turnover = sum(abs(target_weights.get(t, 0.0) - current_weights.get(t, 0.0)) for t in target_weights) / 2.0
        if raw_turnover <= max_turnover:
            return target_weights

        # Scale step size back toward current_weights
        shrink_factor = max_turnover / max(raw_turnover, 1e-6)
        adjusted = {}
        for t in target_weights:
            cw = current_weights.get(t, 0.0)
            tw = target_weights[t]
            adjusted[t] = cw + (tw - cw) * shrink_factor

        # Re-normalize
        total_adj = sum(adjusted.values())
        return {t: round(w / total_adj, 6) for t, w in adjusted.items()}

    # -------------------------------------------------------------------------
    # 4. generate_actions()
    # -------------------------------------------------------------------------
    def generate_actions(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        threshold: float = 0.0025
    ) -> Dict[str, RebalanceAction]:
        """
        Determines rebalancing action (INCREASE, HOLD, REDUCE) based on the threshold.
        Default threshold: 0.25% (0.0025).
        """
        actions: Dict[str, RebalanceAction] = {}

        for ticker, target_w in target_weights.items():
            current_w = current_weights.get(ticker, 0.0)
            delta = target_w - current_w

            if delta > threshold:
                actions[ticker] = RebalanceAction.INCREASE
            elif delta < -threshold:
                actions[ticker] = RebalanceAction.REDUCE
            else:
                actions[ticker] = RebalanceAction.HOLD

        return actions

    # -------------------------------------------------------------------------
    # 5. generate_explanations()
    # -------------------------------------------------------------------------
    def generate_explanations(
        self,
        ticker: str,
        current_weight: float,
        target_weight: float,
        signal_data: Dict[str, Any],
        action: RebalanceAction
    ) -> str:
        """
        Generates plain-English, auditable explanation detailing why each stock weight changed.
        """
        cur_pct = round(current_weight * 100.0, 2)
        tgt_pct = round(target_weight * 100.0, 2)
        delta_pct = round((target_weight - current_weight) * 100.0, 2)
        delta_str = f"+{delta_pct:.2f}%" if delta_pct > 0 else f"{delta_pct:.2f}%"

        sent = signal_data.get("avg_sentiment", 0.0)
        impact = signal_data.get("avg_impact", 5.0)
        event = signal_data.get("dominant_event", "Other")
        sig_count = signal_data.get("signal_count", 0)
        ret = signal_data.get("recent_return", 0.0)
        ret_pct = f"{ret * 100.0:+.1f}%"

        if action == RebalanceAction.REDUCE:
            reason = (
                f"Weight reduced from {cur_pct:.2f}% to {tgt_pct:.2f}% ({delta_str}) because the stock "
                f"exhibited negative news sentiment ({sent:+.2f}) with significant event impact ({impact}/10) "
                f"classified as '{event}' across {sig_count} news signal(s), coupled with recent return momentum ({ret_pct})."
            )
        elif action == RebalanceAction.INCREASE:
            reason = (
                f"Weight increased from {cur_pct:.2f}% to {tgt_pct:.2f}% ({delta_str}) driven by strong positive "
                f"news sentiment ({sent:+.2f}), favorable event classification '{event}' (impact {impact}/10), "
                f"and positive market momentum ({ret_pct})."
            )
        else:  # HOLD
            if sig_count == 0:
                reason = (
                    f"Weight maintained at {cur_pct:.2f}% (delta {delta_str} within threshold) as no disruptive "
                    f"news signals were detected. Defaulted to neutral benchmark weight."
                )
            else:
                reason = (
                    f"Weight held steady at {cur_pct:.2f}% (delta {delta_str} within threshold) as net sentiment "
                    f"({sent:+.2f}) and impact ({impact}/10) in '{event}' remained within the neutral band."
                )

        return reason

    # -------------------------------------------------------------------------
    # Orchestration: rebalance()
    # -------------------------------------------------------------------------
    def rebalance(
        self,
        signals_by_ticker: Optional[Dict[str, List[RiskSignal]]] = None,
        custom_current_weights: Optional[Dict[str, float]] = None,
        config: Optional[RebalanceRequest] = None
    ) -> RebalanceSummary:
        """
        Executes complete end-to-end tactical rebalancing workflow across the mock index universe.
        """
        req = config or RebalanceRequest()
        tickers = list(self.DEFAULT_UNIVERSE.keys())
        n = len(tickers)

        # Baseline equal weights if no custom current weights provided
        if custom_current_weights:
            current_weights = {t: custom_current_weights.get(t, 1.0 / n) for t in tickers}
            norm = sum(current_weights.values())
            current_weights = {t: round(w / norm, 6) for t, w in current_weights.items()}
        else:
            current_weights = {t: round(1.0 / n, 6) for t in tickers}

        # Step 1: Calculate Tactical Signals for each constituent
        tactical_signals: Dict[str, float] = {}
        signal_details: Dict[str, Dict[str, Any]] = {}
        market_quotes: Dict[str, TickerMarketData] = {}

        for ticker in tickers:
            m_quote = self.market_service.get_stock_quote(ticker)
            market_quotes[ticker] = m_quote
            ticker_signals = (signals_by_ticker or {}).get(ticker, [])

            sig_calc = self.calculate_signal(ticker, ticker_signals, m_quote)
            tactical_signals[ticker] = sig_calc["tactical_signal"]
            signal_details[ticker] = sig_calc

        # Step 2: Calculate Raw Target Weights
        raw_targets = self.calculate_target_weights(current_weights, tactical_signals)

        # Step 3: Apply Constraints (Floor, Cap, Sum = 100%, Turnover Limit)
        constrained_targets = self.apply_constraints(
            raw_weights=raw_targets,
            min_weight=req.min_weight,
            max_weight=req.max_weight,
            max_turnover=req.max_turnover,
            current_weights=current_weights
        )

        # Step 4: Generate Actions (INCREASE, HOLD, REDUCE)
        actions = self.generate_actions(
            current_weights=current_weights,
            target_weights=constrained_targets,
            threshold=req.action_threshold
        )

        # Step 5: Generate Explanations & Assemble Constituents
        constituents: List[ConstituentRebalanceDetail] = []
        action_counts = {"INCREASE": 0, "HOLD": 0, "REDUCE": 0}

        for ticker in tickers:
            act = actions[ticker]
            action_counts[act.value] += 1
            info = self.DEFAULT_UNIVERSE[ticker]
            sig_d = signal_details[ticker]
            mq = market_quotes[ticker]

            cur_w = current_weights[ticker]
            tgt_w = constrained_targets[ticker]
            delta_pct = round((tgt_w - cur_w) * 100.0, 2)

            explanation = self.generate_explanations(
                ticker=ticker,
                current_weight=cur_w,
                target_weight=tgt_w,
                signal_data=sig_d,
                action=act
            )

            # Price from market data or default benchmark
            price = mq.current_price if mq and mq.current_price else 150.0

            constituents.append(
                ConstituentRebalanceDetail(
                    ticker=ticker,
                    company_name=info["name"],
                    sector=info["sector"],
                    current_price=price,
                    current_index_weight=cur_w,
                    current_weight_pct=round(cur_w * 100.0, 2),
                    target_weight=tgt_w,
                    target_weight_pct=round(tgt_w * 100.0, 2),
                    weight_delta_pct=delta_pct,
                    recent_return=sig_d["recent_return"],
                    volatility=sig_d["volatility"],
                    latest_sentiment_score=sig_d["avg_sentiment"],
                    latest_impact_score=sig_d["avg_impact"],
                    latest_event_type=sig_d["dominant_event"],
                    calculated_risk_signal=sig_d["tactical_signal"],
                    rebalance_action=act,
                    explanation=explanation
                )
            )

        # Turnover calculation: sum(|tgt - cur|) / 2 in %
        turnover_pct = round(
            sum(abs(constrained_targets[t] - current_weights[t]) for t in tickers) / 2.0 * 100.0,
            2
        )

        # Top increased & reduced
        sorted_by_delta = sorted(constituents, key=lambda c: c.weight_delta_pct, reverse=True)
        top_increased = [c.ticker for c in sorted_by_delta if c.weight_delta_pct > 0][:3]
        top_reduced = [c.ticker for c in reversed(sorted_by_delta) if c.weight_delta_pct < 0][:3]

        all_sentiments = [sig_d["avg_sentiment"] for sig_d in signal_details.values()]
        all_impacts = [sig_d["avg_impact"] for sig_d in signal_details.values()]

        return RebalanceSummary(
            as_of=utc_now(),
            universe_size=n,
            total_current_weight_pct=round(sum(current_weights.values()) * 100.0, 2),
            total_target_weight_pct=round(sum(constrained_targets.values()) * 100.0, 2),
            turnover_pct=turnover_pct,
            actions_count=action_counts,
            average_sentiment=round(sum(all_sentiments) / n, 4),
            average_impact=round(sum(all_impacts) / n, 1),
            top_increased=top_increased,
            top_reduced=top_reduced,
            constituents=constituents,
            methodology=self.DISCLAIMER
        )
