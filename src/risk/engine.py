from src.core.contracts.spec import InstrumentSpec
from src.core.types.strategy import TradeIdea, RegimeType
from .asset_aware_risk import MultiAssetRiskEngine
from typing import Dict

class RiskEngine:
    """
    Primary interface for risk validation and position sizing.
    Wraps MultiAssetRiskEngine for advanced features.
    """
    def __init__(self, specs: Dict[str, InstrumentSpec], risk_per_trade: float = 0.01):
        self.internal_engine = MultiAssetRiskEngine(specs, risk_per_trade)

    def validate(self, idea: TradeIdea, size: float, equity: float, spread: float = 0.0) -> bool:
        valid, _ = self.internal_engine.validate_trade(idea, size, equity, spread)
        return valid

    def position_size(self, 
                      symbol: str, 
                      volatility: float, 
                      equity: float, 
                      stop_dist: float, 
                      regime: Any, 
                      confidence: float = 0.5, 
                      rr: float = 2.0) -> float:
        return self.internal_engine.get_position_sizing(symbol, volatility, equity, stop_dist, regime, confidence, rr)
