from src.core.contracts.spec import InstrumentSpec
from src.core.types.strategy import TradeIdea, RegimeType
from .asset_aware_risk import MultiAssetRiskEngine
from src.infra.database.repositories.decision_repo import DecisionRepository
from typing import Dict, Any

class RiskEngine:
    """
    Primary interface for risk validation and position sizing.
    Wraps MultiAssetRiskEngine for advanced features.
    """
    def __init__(self, specs: Dict[str, InstrumentSpec], risk_per_trade: float = 0.01):
        self.internal_engine = MultiAssetRiskEngine(specs, risk_per_trade)

    def validate(self, idea: TradeIdea, size: float, equity: float, spread: float = 0.0) -> bool:
        valid, reason = self.internal_engine.validate_trade(idea, size, equity, spread)
        
        # Log Decision (Phase 6)
        DecisionRepository.log_risk_decision({
            "candidate_id": str(idea.id) if hasattr(idea, 'id') else "N/A",
            "risk_score": 0.0, # Placeholder for specific score
            "position_size": size,
            "stop_distance": abs(idea.entry_price - idea.stop_loss) if idea.stop_loss else None,
            "take_profit_distance": abs(idea.entry_price - idea.take_profit) if idea.take_profit else None,
            "is_approved": valid,
            "reason": reason
        })
        
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
