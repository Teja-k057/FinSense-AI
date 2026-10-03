import math
import numpy as np
from typing import Dict, Any

class RiskMetricsCalculator:
    """Calculates Parametric and Stressed Value at Risk (VaR) and Expected Shortfall (CVaR)."""

    Z_SCORES = {
        0.90: 1.2816,
        0.95: 1.6449,
        0.99: 2.3263,
        0.999: 3.0902
    }

    @classmethod
    def calculate_var_cvar(
        cls,
        portfolio_value: float,
        portfolio_volatility_annual: float,
        confidence: float = 0.95,
        horizon_days: int = 1,
        mean_return_annual: float = 0.0
    ) -> Dict[str, float]:
        """Calculates 1-day (or N-day) Parametric VaR and CVaR."""
        # Convert annual vol to horizon vol
        dt = horizon_days / 252.0
        sigma_t = portfolio_volatility_annual * math.sqrt(dt)
        mu_t = mean_return_annual * dt

        z = cls.Z_SCORES.get(confidence, 1.6449)

        # Standard normal PDF phi(z)
        phi_z = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * (z ** 2))

        # VaR as positive dollar loss
        var_pct = (z * sigma_t) - mu_t
        var_dollars = max(0.0, portfolio_value * var_pct)

        # CVaR (Expected Shortfall) = E[Loss | Loss > VaR]
        cvar_pct = ((phi_z / (1.0 - confidence)) * sigma_t) - mu_t
        cvar_dollars = max(var_dollars * 1.05, portfolio_value * cvar_pct)

        return {
            "var_dollars": round(var_dollars, 2),
            "var_pct": round(var_pct, 4),
            "cvar_dollars": round(cvar_dollars, 2),
            "cvar_pct": round(cvar_pct, 4),
            "confidence": confidence,
            "horizon_days": horizon_days
        }
