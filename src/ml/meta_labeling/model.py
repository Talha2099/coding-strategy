from typing import Dict
from src.core.math_engine.stochastic_processes import MonteCarloEngine, GeometricBrownianMotion
from src.core.math_engine.time_series import GARCH11
import numpy as np

class MetaModel:
    def __init__(self, model_instance=None):
        self.model = model_instance # Scikit-learn or similar instance
        self.vola_forecast = GARCH11(omega=0.000001, alpha=0.1, beta=0.8)
        self.mc_engine = MonteCarloEngine(n_paths=1000)

    def predict(self, features: Dict[str, any]) -> float:
        """
        Predict the probability of a signal being profitable using asset context, session, and trend.
        Now context-aware for CFDs vs Stocks.
        """
        ofi = float(features.get("ofi", 0.0))
        vol = float(features.get("volatility", 0.001))
        trend_strength = float(features.get("trend_strength", 0.0))
        asset_class = features.get("asset_class", "cfd")
        session = features.get("session", "london")
        
        # 1. Update Volatility Forecast
        forecasted_vol = self.vola_forecast.forecast(vol)
        
        # 2. Monte Carlo edge estimation with trend bias
        # Higher trend strength increases the drift component in simulation
        drift = (ofi * 0.01) + (trend_strength * 0.05)
        gbm = GeometricBrownianMotion(mu=drift, sigma=forecasted_vol)
        paths = self.mc_engine.simulate(
            start_price=1.0, 
            steps=50, 
            dt=1/252, 
            process_func=gbm.next_step
        )
        
        prob_up = np.mean(paths[:, -1] > 1.0)
        
        # 3. Contextual Calibration
        # Penalize illiquid sessions (Close/Asia for some assets)
        session_penalty = 0.0
        if session in ["close", "asia"] and asset_class == "stock":
            session_penalty = -0.15
        elif session == "overlap_ln_ny":
            session_penalty = +0.05 # Bonus for high liquidity
            
        # 4. Base Heuristic Score
        score = 0.5
        score += ofi * 0.1
        score += trend_strength * 0.2 # Significant weight on momentum trend
        score += session_penalty
        
        # Blend with Monte Carlo
        final_prob = 0.6 * score + 0.4 * prob_up
            
        return float(max(0.01, min(0.99, final_prob)))
