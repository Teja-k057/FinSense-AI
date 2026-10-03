import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.rebalancer.models import RebalanceRequest
from backend.app.rebalancer.backtest_models import (
    BacktestRequest,
    BacktestFrequency,
    PeriodBacktestPoint,
    StrategyPerformanceMetrics,
    BacktestComparisonResult
)
from backend.app.rebalancer.rebalancing_engine import RebalancingEngine
from backend.app.portfolio.market_data import MarketDataService
from backend.app.portfolio.models import TickerMarketData
from backend.app.schemas.nlp_schemas import RiskSignal
from backend.app.database.models import RiskSignal as DBRiskSignal

logger = logging.getLogger("rebalancer.backtester")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class HistoricalBacktester:
    """
    Simulates historical tactical index rebalancing for MODULE A.
    
    Compares:
    1. BASELINE: Equal-weighted mock index without NLP tactical rebalancing.
    2. NLP STRATEGY: Tactically rebalanced using AI/NLP Risk Engine signals and market data.
    
    STRICT ANTI-LOOK-AHEAD BIAS ENFORCEMENT:
    At simulated rebalance date t_k, ONLY news signals and prices with timestamp <= t_k
    are visible. Subsequent returns are evaluated strictly across (t_k -> t_{k+1}).
    
    DISCLAIMER:
    Academic Hackathon Research & Simulation Prototype for the S&P Global x CRISIL Competition.
    Not a claim of future investment performance or financial/trading advice.
    """

    DISCLAIMER = (
        "Tactical Index Historical Backtesting Simulation "
        "(Academic Hackathon Model - Not Financial or Investment Advice)"
    )

    ASSUMPTIONS = {
        "execution_model": "Close-to-Close subsequent period return evaluation.",
        "transaction_costs": "10.0 bps (0.10%) per 100% portfolio turnover deducted directly from returns.",
        "rebalance_execution": "Target weights determined at Close of date t_k; applied to subsequent period (t_k to t_{k+1}).",
        "lookahead_prevention": "Point-in-time news filter: strictly signals published <= rebalance timestamp.",
        "baseline_index": "15-stock equal-weighted mock index (6.67% baseline per stock).",
        "market_impact": "Zero price market impact assumed (price taker simulation)."
    }

    LIMITATIONS = [
        "Historical news density: Free open data sources (GDELT free API & public PhraseBank) provide variable historical news depth compared to proprietary institutional feeds.",
        "GDELT rolling window: Live GDELT free tier is optimized for rolling 7–30 day live feeds; historical signals prior to the window rely on local database caches.",
        "Liquidity: Backtest assumes full execution at historical closing prices without execution slippage beyond the 10 bps model."
    ]

    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        rebalancing_engine: Optional[RebalancingEngine] = None
    ):
        self.market_service = market_data_service or MarketDataService()
        self.rebalancer = rebalancing_engine or RebalancingEngine(self.market_service)

    def run_backtest(
        self,
        request: Optional[BacktestRequest] = None,
        db: Optional[Session] = None
    ) -> BacktestComparisonResult:
        """Executes full historical comparative simulation."""
        req = request or BacktestRequest()
        tickers = list(self.rebalancer.DEFAULT_UNIVERSE.keys())
        n_assets = len(tickers)

        # Step 1: Collect Historical Market Prices for all 15 constituents
        price_history_by_ticker: Dict[str, Dict[str, float]] = {}
        all_dates_set = set()

        for ticker in tickers:
            quote = self.market_service.get_stock_quote(ticker, period=req.period)
            prices = {}
            if quote and quote.historical_prices:
                for hp in quote.historical_prices:
                    prices[hp.date] = hp.close
                    all_dates_set.add(hp.date)
            price_history_by_ticker[ticker] = prices

        sorted_dates = sorted(list(all_dates_set))
        if len(sorted_dates) < 3:
            logger.warning("[Backtester] Insufficient historical dates retrieved from market data. Generating baseline fallback.")
            # Create synthetic fallback date steps if yfinance is offline or market closed
            today = datetime.now()
            sorted_dates = [(today - timedelta(days=21 - i * 7)).strftime("%Y-%m-%d") for i in range(4)]
            for ticker in tickers:
                base_p = 100.0 + (hash(ticker) % 50)
                price_history_by_ticker[ticker] = {
                    d: round(base_p * (1.0 + (i * 0.005)), 2) for i, d in enumerate(sorted_dates)
                }

        # Step 2: Determine Rebalance Interval Steps (e.g. Weekly: every 5 trading days)
        step = 5 if req.rebalance_frequency == BacktestFrequency.WEEKLY else (
            1 if req.rebalance_frequency == BacktestFrequency.DAILY else 21
        )
        rebalance_indices = list(range(0, len(sorted_dates) - 1, step))
        if len(rebalance_indices) < 2:
            rebalance_indices = [0, len(sorted_dates) - 1]

        # Step 3: Fetch Historical News Signals from Database if available
        all_signals: List[RiskSignal] = []
        if db:
            try:
                db_signals = db.query(DBRiskSignal).order_by(DBRiskSignal.created_at.asc()).all()
                all_signals = [_map_db_to_signal(s, db) for s in db_signals]
            except Exception as e:
                logger.debug(f"[Backtester] DB signals query: {e}")

        # Step 4: Iterative Time-Stepped Simulation
        baseline_cum_wealth = 1.0
        nlp_cum_wealth = 1.0
        baseline_returns: List[float] = []
        nlp_returns: List[float] = []
        turnover_series: List[float] = []
        trajectory: List[PeriodBacktestPoint] = []

        current_nlp_weights = {t: 1.0 / n_assets for t in tickers}
        baseline_weights = {t: 1.0 / n_assets for t in tickers}

        for idx, start_i in enumerate(rebalance_indices):
            # End index for this holding period
            if idx + 1 < len(rebalance_indices):
                end_i = rebalance_indices[idx + 1]
            else:
                end_i = len(sorted_dates) - 1

            if start_i >= end_i:
                continue

            t_rebalance = sorted_dates[start_i]
            t_subsequent = sorted_dates[end_i]

            # Parse rebalance date for point-in-time filtering
            try:
                t_rebal_dt = datetime.strptime(t_rebalance, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                t_rebal_dt = utc_now()

            # Anti-Look-Ahead Bias: Only use signals strictly published <= t_rebal_dt
            lookback_window = t_rebal_dt - timedelta(days=30)
            available_signals: Dict[str, List[RiskSignal]] = {}
            total_signals_used = 0

            for sig in all_signals:
                sig_dt = sig.timestamp
                if sig_dt.tzinfo is None:
                    sig_dt = sig_dt.replace(tzinfo=timezone.utc)
                if sig_dt <= t_rebal_dt and sig_dt >= lookback_window:
                    tkr = sig.company.upper().strip()
                    if tkr not in available_signals:
                        available_signals[tkr] = []
                    available_signals[tkr].append(sig)
                    total_signals_used += 1

            # Execute NLP Rebalancing Decision at t_rebalance
            rebal_config = RebalanceRequest(
                min_weight=req.min_weight,
                max_weight=req.max_weight,
                action_threshold=req.action_threshold
            )
            rebal_summary = self.rebalancer.rebalance(
                signals_by_ticker=available_signals,
                custom_current_weights=current_nlp_weights,
                config=rebal_config
            )

            new_nlp_weights = {c.ticker: c.target_weight for c in rebal_summary.constituents}

            # Calculate period turnover & transaction fees
            period_turnover = sum(
                abs(new_nlp_weights.get(t, 0.0) - current_nlp_weights.get(t, 0.0)) for t in tickers
            ) / 2.0
            turnover_series.append(period_turnover)

            tc_fee_pct = period_turnover * (req.transaction_cost_bps / 10000.0)

            # Step 5: Evaluate Subsequent Stock Returns from t_rebalance to t_subsequent
            stock_returns: Dict[str, float] = {}
            for tkr in tickers:
                p_start = price_history_by_ticker.get(tkr, {}).get(t_rebalance)
                p_end = price_history_by_ticker.get(tkr, {}).get(t_subsequent)

                if p_start and p_end and p_start > 0:
                    ret = (p_end - p_start) / p_start
                else:
                    ret = 0.0
                stock_returns[tkr] = ret

            # Compute Portfolio Period Returns
            baseline_period_ret = sum(baseline_weights[t] * stock_returns[t] for t in tickers)
            nlp_period_ret = sum(new_nlp_weights[t] * stock_returns[t] for t in tickers) - tc_fee_pct

            baseline_returns.append(baseline_period_ret)
            nlp_returns.append(nlp_period_ret)

            # Accumulate wealth
            baseline_cum_wealth *= (1.0 + baseline_period_ret)
            nlp_cum_wealth *= (1.0 + nlp_period_ret)

            # Record trajectory step
            active_ret = nlp_period_ret - baseline_period_ret

            sorted_tilts = sorted(
                new_nlp_weights.keys(),
                key=lambda t: new_nlp_weights[t] - baseline_weights[t],
                reverse=True
            )
            top_over = [t for t in sorted_tilts if new_nlp_weights[t] > baseline_weights[t]][:2]
            top_under = [t for t in reversed(sorted_tilts) if new_nlp_weights[t] < baseline_weights[t]][:2]

            trajectory.append(
                PeriodBacktestPoint(
                    period_index=len(trajectory) + 1,
                    date=t_subsequent,
                    rebalance_date=t_rebalance,
                    subsequent_date=t_subsequent,
                    baseline_period_return_pct=round(baseline_period_ret * 100.0, 2),
                    nlp_period_return_pct=round(nlp_period_ret * 100.0, 2),
                    active_period_return_pct=round(active_ret * 100.0, 2),
                    baseline_cumulative_return_pct=round((baseline_cum_wealth - 1.0) * 100.0, 2),
                    nlp_cumulative_return_pct=round((nlp_cum_wealth - 1.0) * 100.0, 2),
                    turnover_pct=round(period_turnover * 100.0, 2),
                    transaction_cost_pct=round(tc_fee_pct * 100.0, 3),
                    top_overweight=top_over,
                    top_underweight=top_under,
                    news_signals_used=total_signals_used
                )
            )

            # Advance state
            current_nlp_weights = new_nlp_weights

        # Step 6: Compute Full Performance Metrics for Both Strategies
        periods_per_year = 52.0 if req.rebalance_frequency == BacktestFrequency.WEEKLY else (
            252.0 if req.rebalance_frequency == BacktestFrequency.DAILY else 12.0
        )

        base_metrics = self._calculate_metrics(baseline_returns, periods_per_year, turnover=0.0)
        nlp_metrics = self._calculate_metrics(
            nlp_returns,
            periods_per_year,
            turnover=sum(turnover_series) * 100.0,
            comp_returns=baseline_returns
        )

        outperformance = round(nlp_metrics.cumulative_return_pct - base_metrics.cumulative_return_pct, 2)

        return BacktestComparisonResult(
            as_of=utc_now(),
            start_date=sorted_dates[0],
            end_date=sorted_dates[-1],
            rebalance_frequency=req.rebalance_frequency.value,
            total_periods=len(trajectory),
            universe_size=n_assets,
            baseline_metrics=base_metrics,
            nlp_strategy_metrics=nlp_metrics,
            outperformance_pct=outperformance,
            trajectory=trajectory,
            assumptions=self.ASSUMPTIONS,
            limitations=self.LIMITATIONS,
            disclaimer=self.DISCLAIMER
        )

    def _calculate_metrics(
        self,
        returns: List[float],
        periods_per_year: float,
        turnover: float = 0.0,
        comp_returns: Optional[List[float]] = None
    ) -> StrategyPerformanceMetrics:
        """Computes cumulative return, annualized return, volatility, max drawdown, Sharpe, and win rate."""
        if not returns:
            return StrategyPerformanceMetrics(
                cumulative_return_pct=0.0,
                annualized_return_pct=0.0,
                annualized_volatility_pct=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                total_turnover_pct=0.0,
                win_rate_pct=50.0
            )

        n = len(returns)
        # Cumulative Wealth
        wealth = [1.0]
        for r in returns:
            wealth.append(wealth[-1] * (1.0 + r))

        cum_return = wealth[-1] - 1.0

        # Annualized Return
        if n > 0 and wealth[-1] > 0:
            ann_return = (wealth[-1] ** (periods_per_year / max(1, n))) - 1.0
        else:
            ann_return = 0.0

        # Volatility
        mean_r = sum(returns) / n
        var_r = sum((r - mean_r) ** 2 for r in returns) / max(1, n - 1)
        std_r = math.sqrt(var_r)
        ann_vol = std_r * math.sqrt(periods_per_year)

        # Maximum Drawdown (Peak to trough)
        peak = 1.0
        max_dd = 0.0
        for w in wealth:
            if w > peak:
                peak = w
            dd = (w - peak) / peak
            if dd < max_dd:
                max_dd = dd

        # Sharpe Ratio (assumes 0.0% risk free benchmark)
        sharpe = (ann_return / ann_vol) if ann_vol > 1e-6 else 0.0

        # Win Rate against baseline
        win_rate = 50.0
        if comp_returns and len(comp_returns) == n:
            wins = sum(1 for r_nlp, r_base in zip(returns, comp_returns) if r_nlp > r_base)
            win_rate = round((wins / n) * 100.0, 1)

        return StrategyPerformanceMetrics(
            cumulative_return_pct=round(cum_return * 100.0, 2),
            annualized_return_pct=round(ann_return * 100.0, 2),
            annualized_volatility_pct=round(ann_vol * 100.0, 2),
            max_drawdown_pct=round(abs(max_dd) * 100.0, 2),
            sharpe_ratio=round(sharpe, 2),
            total_turnover_pct=round(turnover, 2),
            win_rate_pct=win_rate
        )
