from typing import List, Dict, Optional, Any
import numpy as np
from src.core.types.strategy import TradeIdea, RegimeType
from src.risk.asset_aware_risk import MultiAssetRiskEngine
from src.ml.meta_labeling.model import MetaModel

class PortfolioManager:
    """
    Orchestrates multiple strategy outputs, nets exposure, and ranks opportunities.
    Uses meta-labeling and regime-aware logic to suppress conflicts.
    """
    def __init__(self, risk_engine: MultiAssetRiskEngine, meta_model: MetaModel):
        self.risk_engine = risk_engine
        self.meta_model = meta_model
        self.pending_ideas: List[TradeIdea] = []
        self.active_positions: Dict[str, float] = {} # Symbol -> Quantity
        self.strategy_returns: Dict[str, float] = {} # StrategyName -> Cumulative Return for prioritization

    def process_ideas(self, ideas: List[TradeIdea], equity: float, regime_state: Any) -> List[TradeIdea]:
        """
        Ranks ideas by quality (MetaScore * RR) and filters for regime-conflicts.
        """
        if not ideas: return []
        
        from src.core.types.strategy import RegimeType, StrategyFamily
        regime = RegimeType(regime_state.regime_type)

        # 1. Meta-Labeling Layer & Enrichment
        for idea in ideas:
            features = {
                "volatility": regime_state.volatility,
                "trend_strength": regime_state.trend_strength,
                "health": getattr(regime_state, "health_score", 0.5),
                "overextension": getattr(regime_state, "overextension", 0.0)
            }
            meta_prob = self.meta_model.predict(features, regime, idea.strategy_family)
            idea.confidence_score = meta_prob

        # 2. Signal Suppression Logic
        # - In strong trends, suppress Mean Reversion against the trend
        # - In range, suppress Breakout until volatility compresses
        filtered_ideas = []
        for idea in ideas:
            # Rule: Don't mean revert against strong trends
            if regime in [RegimeType.TREND_UP, RegimeType.TREND_DOWN, RegimeType.MID_TREND]:
                is_mr = idea.strategy_family in [StrategyFamily.MEAN_REVERSION, StrategyFamily.RANGE]
                trend_dir = 1 if regime_state.direction == 1 else -1
                trade_dir = 1 if idea.direction == "long" else -1
                
                if is_mr and trend_dir != 0 and trade_dir != trend_dir:
                    # Suppressing counter-trend mean reversion in strong trends
                    continue
            
            # Rule: Suppress breakouts in range if health is low
            if regime == RegimeType.RANGE and idea.strategy_family == StrategyFamily.BREAKOUT:
                if getattr(regime_state, "health_score", 1.0) < 0.6:
                    continue

            filtered_ideas.append(idea)

        # 3. Ranking by Expectancy
        def get_expectancy(idea: TradeIdea):
            p = idea.confidence_score
            return (p * idea.risk_reward_ratio) - (1 - p)

        ranked_ideas = sorted(filtered_ideas, key=get_expectancy, reverse=True)

        # 4. Correlation and Aggregate Risk Filter
        final_selections = []
        seen_symbols = set()
        total_delta = self._calculate_current_delta()

        for idea in ranked_ideas:
            if idea.symbol in seen_symbols: continue
            
            # Filter low expectancy
            if get_expectancy(idea) < 0.1: continue

            # Directional Risk Check
            trade_dir = 1 if idea.direction == "long" else -1
            # If already heavily long, suppress further long entry
            if abs(total_delta + trade_dir) > 5: # Max 5 concurrent directional units
                 continue
            
            existing_pos = self.active_positions.get(idea.symbol, 0.0)
            is_contradictory = (existing_pos > 0 and idea.direction == "short") or \
                               (existing_pos < 0 and idea.direction == "long")
            
            if is_contradictory: continue
            
            final_selections.append(idea)
            seen_symbols.add(idea.symbol)
            total_delta += trade_dir

        return final_selections

    def _calculate_current_delta(self) -> float:
        """Returns aggregate directional exposure (-inf to +inf)."""
        delta = 0.0
        for symbol, qty in self.active_positions.items():
            if qty > 0: delta += 1
            elif qty < 0: delta -= 1
        return delta

    def update_positions(self, symbol: str, quantity: float):
        self.active_positions[symbol] = quantity

    def get_net_exposure(self) -> float:
        return sum(abs(v) for v in self.active_positions.values())
