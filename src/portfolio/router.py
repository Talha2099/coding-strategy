from typing import List, Dict, Optional, Any
import numpy as np
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import RegimeState
from src.core.contracts.instrument_registry import InstrumentRegistry
from src.core.contracts.strategy_matrix import StrategyCompatibilityMatrix
from src.core.contracts.instrument_spec import SessionType

class PortfolioRouter:
    """
    PHASE 12: Advanced Portfolio Router.
    Allocates capital and prioritizes trade ideas based on instrument fit and environment.
    """
    def __init__(self, base_equity: float = 100000.0):
        self.base_equity = base_equity
        self.active_exposure: Dict[str, float] = {} # Symbol -> Exposure $
        
    def route_ideas(self, 
                   ideas: List[TradeIdea], 
                   regime_states: Dict[str, RegimeState],
                   available_equity: float) -> List[TradeIdea]:
        """
        Filters and prioritizes ideas for the entire portfolio.
        """
        if not ideas: return []
        
        scored_ideas = []
        
        for idea in ideas:
            symbol = idea.symbol
            spec = InstrumentRegistry.get_spec(symbol)
            regime_state = regime_states.get(symbol)
            if not regime_state: continue
            
            # 1. INSTRUMENT-STRATEGY COMPATIBILITY SCORE
            # Deriving session from timestamp or defaulting
            session = InstrumentRegistry.get_session(regime_state.timestamp, symbol)
            
            matrix_score = StrategyCompatibilityMatrix.get_suitability_score(
                strategy_family=idea.strategy_family,
                archetype=spec.behavior.archetype,
                regime=RegimeType(regime_state.regime_type),
                session=session,
                volatility=getattr(regime_state, "volatility", 0.2),
                trend_strength=getattr(regime_state, "trend_strength", 0.5)
            )
            
            # 2. SEVERITY FILTER (Hostile Check)
            # If the compatibility score is too low, suppress the strategy immediately
            if matrix_score < 0.3:
                continue
                
            # 3. PRIORITY CALCULATION
            # Priority = (Expectancy * Matrix Score) * Confidence
            expectancy = (idea.confidence_score * idea.risk_reward_ratio) - (1 - idea.confidence_score)
            priority = expectancy * matrix_score * idea.confidence_score
            
            scored_ideas.append({
                "idea": idea,
                "priority": priority,
                "matrix_score": matrix_score,
                "asset_class": spec.asset_class
            })
            
        # 4. RANKING
        ranked_ideas = sorted(scored_ideas, key=lambda x: x["priority"], reverse=True)
        
        # 5. ALLOCATION & CONCENTRATION CONTROL
        final_ideas = []
        seen_asset_classes = {}
        total_risk_commitment = 0.0
        
        for item in ranked_ideas:
            idea = item["idea"]
            priority = item["priority"]
            matrix_score = item["matrix_score"]
            asset_class = item["asset_class"]
            
            # Limit concentration per asset class
            seen_asset_classes[asset_class] = seen_asset_classes.get(asset_class, 0) + 1
            if seen_asset_classes[asset_class] > 3: # Max 3 trades per asset class
                continue
                
            # Reduce risk if priority is marginal
            if priority < 0.2:
                continue
                
            # Check for conflicting ideas on same symbol (already filtered in strategy engines normally, but here as safety)
            if any(f.symbol == idea.symbol for f in final_ideas):
                continue
                
            final_ideas.append(idea)
            
        return final_ideas

    def get_allocation_multiplier(self, symbol: str, strategy_family: StrategyFamily, regime_state: RegimeState) -> float:
        """
        Determines how aggressively to size based on the instrument-strategy fit.
        """
        spec = InstrumentRegistry.get_spec(symbol)
        session = InstrumentRegistry.get_session(regime_state.timestamp, symbol)
        
        matrix_score = StrategyCompatibilityMatrix.get_suitability_score(
            strategy_family=strategy_family,
            archetype=spec.behavior.archetype,
            regime=RegimeType(regime_state.regime_type),
            session=session,
            volatility=getattr(regime_state, "volatility", 0.2),
            trend_strength=getattr(regime_state, "trend_strength", 0.5)
        )
        
        # Higher compatibility -> Higher multiplier
        # 0.5 (Neutral) -> 1.0x
        # 1.0 (Perfect) -> 1.5x
        # 0.3 (Weak) -> 0.5x
        return 0.5 + matrix_score
