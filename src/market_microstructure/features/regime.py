from enum import Enum
from typing import Literal

class LiquidityRegime(Enum):
    HIGH_LIQUIDITY = "high_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    TOXIC_FLOW = "toxic_flow"
    TRENDING = "trend"
    MEAN_REVERSION = "mean_reversion"

def classify_regime(spread: float, ofi: float, volatility: float) -> LiquidityRegime:
    """
    Classifies the current market microstructure regime.
    """
    if spread > 0.0005:
        return LiquidityRegime.LOW_LIQUIDITY
    if abs(ofi) > 0.8:
        return LiquidityRegime.TOXIC_FLOW
    if volatility > 0.001:
        return LiquidityRegime.TRENDING
        
    return LiquidityRegime.HIGH_LIQUIDITY
