import logging
from typing import Dict, Any, List
import numpy as np

from backend.app.schemas.portfolio_schemas import PortfolioConfig
from backend.app.schemas.stress_schemas import (
    StressSimulationRequest,
    StressSimulationResult,
    AssetImpactDetail
)
from backend.app.stress_testing.scenarios import ScenarioRegistry
from backend.app.stress_testing.metrics import RiskMetricsCalculator
from backend.app.portfolio.market_data import MarketDataManager

logger = logging.getLogger(__name__)

class StressSimulator:
    """Executes multi-scenario stress tests combining NLP signals, market matrices, and factor shocks."""

    def __init__(self):
        self.market_data = MarketDataManager()

    def run_simulation(
        self,
        portfolio: PortfolioConfig,
        request: StressSimulationRequest,
        active_signals: List[Dict[str, Any]] = None
    ) -> StressSimulationResult:
        tickers = [pos.ticker for pos in portfolio.positions]
        weights = np.array([pos.weight for pos in portfolio.positions])
        base_value = portfolio.total_value

        # Normalize weights if slight floating point discrepancy
        if weights.sum() > 0:
            weights = weights / weights.sum()

        # 1. Market stats & Base Volatility
        tickers_ordered, cov_matrix = self.market_data.get_covariance_matrix(tickers)
        base_port_var = float(weights.T @ cov_matrix @ weights)
        base_port_vol = np.sqrt(max(0.0001, base_port_var))

        # Base 95% VaR & CVaR
        base_metrics = RiskMetricsCalculator.calculate_var_cvar(
            portfolio_value=base_value,
            portfolio_volatility_annual=base_port_vol,
            confidence=request.confidence_level
        )

        # 2. Determine Shock Vector
        shocks = {}
        scenario_name = request.scenario

        if request.scenario in ScenarioRegistry.SCENARIOS:
            sc_info = ScenarioRegistry.get_scenario(request.scenario)
            scenario_name = sc_info["name"]
            shocks = sc_info["direct_shocks"].copy()
        elif request.scenario == "NLP_NEWS_SHOCK":
            scenario_name = "Dynamic NLP News Shock"
            # Map NLP signals to shock: Shock = Sentiment * (Impact / 10) * Kappa * Vol
            if active_signals:
                for sig in active_signals:
                    t = sig.get("ticker", "SPY")
                    sent = sig.get("sentiment_score", 0.0)
                    impact = sig.get("impact_score", 5.0)
                    ev_type = sig.get("event_type", "General")
                    kappa = 2.2 if "Credit" in ev_type else (1.8 if "Regulatory" in ev_type else 1.4)
                    
                    direct_shock = sent * (impact / 10.0) * kappa * 0.15
                    shocks[t] = min(shocks.get(t, 0.0), direct_shock)
            if not shocks:
                shocks = {"JPM": -0.12, "AAPL": -0.06, "NVDA": -0.08}
        elif request.scenario == "CUSTOM":
            scenario_name = "Custom What-If Stress Scenario"
            shocks = request.custom_shocks.copy()

        # Apply any explicit user overrides
        if request.custom_shocks:
            shocks.update(request.custom_shocks)

        # 3. Compute Asset-Level Impacts & Contagion
        asset_details: List[AssetImpactDetail] = []
        stressed_asset_values = []

        for pos in portfolio.positions:
            t = pos.ticker
            base_alloc = base_value * pos.weight
            
            # Asset specific shock or sector contagion proxy
            shock = shocks.get(t, shocks.get("SPY", -0.03))
            
            # Factor interest rate adjustment
            if request.factor_rate_shock_bps != 0:
                rate_effect = (request.factor_rate_shock_bps / 10000.0)
                if pos.sector == "Technology":
                    shock -= (rate_effect * 2.0)  # Tech duration sensitivity
                elif pos.sector == "Financials":
                    shock += (rate_effect * 0.5)  # Net interest margin benefit

            # Clamp shock between -95% and +50%
            shock = max(-0.95, min(0.50, shock))
            stressed_alloc = base_alloc * (1.0 + shock)
            pnl_impact = stressed_alloc - base_alloc

            stressed_asset_values.append(stressed_alloc)
            asset_details.append(
                AssetImpactDetail(
                    ticker=t,
                    sector=pos.sector or "General",
                    weight=pos.weight,
                    base_allocation=round(base_alloc, 2),
                    shock_pct=round(shock, 4),
                    pnl_impact=round(pnl_impact, 2),
                    stressed_allocation=round(stressed_alloc, 2)
                )
            )

        stressed_total_value = sum(stressed_asset_values)
        total_pnl_loss = stressed_total_value - base_value
        pnl_loss_pct = total_pnl_loss / base_value if base_value > 0 else 0.0

        # Stressed Volatility & Metrics (Stress increases asset correlation and variance)
        vol_multiplier = 1.8 if total_pnl_loss < 0 else 1.2
        stressed_port_vol = base_port_vol * vol_multiplier
        stressed_metrics = RiskMetricsCalculator.calculate_var_cvar(
            portfolio_value=stressed_total_value,
            portfolio_volatility_annual=stressed_port_vol,
            confidence=request.confidence_level
        )

        # 4. Generate Institutional Recommendations
        recommendations = []
        worst_asset = min(asset_details, key=lambda x: x.shock_pct)
        if worst_asset.shock_pct < -0.10:
            recommendations.append(
                f"Severe vulnerability detected in {worst_asset.ticker} ({worst_asset.shock_pct*100:.1f}% drawdown). "
                f"Consider tightening stop-loss limits or reducing allocation weight."
            )
        if abs(pnl_loss_pct) > 0.05:
            recommendations.append(
                f"Portfolio drawdown ({abs(pnl_loss_pct)*100:.1f}%) exceeds standard 5% risk tolerance. "
                f"Implement downside sector hedging via protective index puts (SPY/XLF)."
            )
        recommendations.append(
            f"Post-shock 1-day 95% Value at Risk surges from ${base_metrics['var_dollars']:,.0f} "
            f"to ${stressed_metrics['var_dollars']:,.0f}. Capital buffer should be fortified."
        )

        return StressSimulationResult(
            scenario_name=scenario_name,
            base_portfolio_value=round(base_value, 2),
            stressed_portfolio_value=round(stressed_total_value, 2),
            pnl_loss_amount=round(total_pnl_loss, 2),
            pnl_loss_pct=round(pnl_loss_pct, 4),
            pre_var_95=base_metrics["var_dollars"],
            post_var_95=stressed_metrics["var_dollars"],
            pre_cvar_95=base_metrics["cvar_dollars"],
            post_cvar_95=stressed_metrics["cvar_dollars"],
            asset_breakdown=asset_details,
            recommendations=recommendations
        )
