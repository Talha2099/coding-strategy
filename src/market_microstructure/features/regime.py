from enum import Enum
from typing import Literal, List
import numpy as np
from src.core.math_engine.markov_bayesian import HiddenMarkovModel

class LiquidityRegime(Enum):
    HIGH_LIQUIDITY = "high_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    TOXIC_FLOW = "toxic_flow"
    TRENDING = "trend"
    MEAN_REVERSION = "mean_reversion"

class RegimeDetector:
    def __init__(self):
        self.hmm = HiddenMarkovModel(n_states=4)
        # Pre-configured emission params for [TrendUp, TrendDown, Range, Toxic]
        self.hmm.emission_params = [
            {"mean": 0.0001, "std": 0.0002},  # Trend Up
            {"mean": -0.0001, "std": 0.0002}, # Trend Down
            {"mean": 0.0, "std": 0.0001},     # Range
            {"mean": 0.0, "std": 0.001}       # Toxic/High Vol
        ]

    def classify(self, returns_history: List[float]) -> LiquidityRegime:
        if len(returns_history) < 20:
            return LiquidityRegime.HIGH_LIQUIDITY
            
        states = self.hmm.decode(np.array(returns_history))
        current_state = states[-1]
        
        mapping = {
            0: LiquidityRegime.TRENDING,
            1: LiquidityRegime.TRENDING,
            2: LiquidityRegime.MEAN_REVERSION,
            3: LiquidityRegime.TOXIC_FLOW
        }
        
        return mapping.get(current_state, LiquidityRegime.HIGH_LIQUIDITY)

def classify_regime(spread: float, ofi: float, volatility: float) -> LiquidityRegime:
    """
    Heuristic-based fallback.
    """
    if spread > 0.0005:
        return LiquidityRegime.LOW_LIQUIDITY
    if abs(ofi) > 0.8:
        return LiquidityRegime.TOXIC_FLOW
    if volatility > 0.001:
        return LiquidityRegime.TRENDING
        
    return LiquidityRegime.HIGH_LIQUIDITY
