from typing import List, Optional, Dict, Any
import numpy as np
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.strategies.base import BaseStrategy

class StrategyRouter:
    """
    Orchestrates strategy families based on market context.
    Selects, suppresses, and ranks trade ideas.
    """
    def __init__(self, strategies: List[BaseStrategy]):
        self.strategies = strategies
        
    def route(self, 
              symbol: str, 
              candles: List[Candle], 
              regime_state: RegimeState, 
              mtf_state: Optional[MTFRegimeState] = None) -> List[TradeIdea]:
        """
        Main entry point for generating ranked trade ideas.
        """
        current_regime = RegimeType(regime_state.regime_type)
        
        # 1. Filter active strategies for this regime
        active_strats = [s for s in self.strategies if s.is_valid_regime(current_regime)]
        
        # 2. Collect setup detection results
        ideas: List[TradeIdea] = []
        for strat in active_strats:
            if strat.detect_setup(candles, regime_state, mtf_state):
                if strat.confirm_entry(candles):
                    idea = strat.build_trade_idea(symbol, candles, regime_state, mtf_state)
                    if idea:
                        ideas.append(idea)
                        
        # 3. Suppress conflicting ideas (e.g. Long vs Short in same asset class)
        final_ideas = self._resolve_conflicts(ideas)
        
        # 4. Rank candidates by confidence score
        final_ideas.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return final_ideas

    def _resolve_conflicts(self, ideas: List[TradeIdea]) -> List[TradeIdea]:
        """
        If multiple strategies generate opposing ideas for the same symbol,
        prefer the one with higher confidence or higher-priority family.
        """
        if not ideas: return []
        
        # Group by symbol
        by_symbol: Dict[str, List[TradeIdea]] = {}
        for idea in ideas:
            if idea.symbol not in by_symbol: by_symbol[idea.symbol] = []
            by_symbol[idea.symbol].append(idea)
            
        resolved: List[TradeIdea] = []
        for symbol, symbol_ideas in by_symbol.items():
            if len(symbol_ideas) == 1:
                resolved.append(symbol_ideas[0])
                continue
                
            # Check for direction conflict
            longs = [i for i in symbol_ideas if i.direction == "long"]
            shorts = [i for i in symbol_ideas if i.direction == "short"]
            
            if longs and shorts:
                # Conflict! Select best idea by confidence
                best_long = max(longs, key=lambda x: x.confidence_score)
                best_short = max(shorts, key=lambda x: x.confidence_score)
                
                # If one has significantly higher confidence, pick it
                if best_long.confidence_score > best_short.confidence_score + 0.1:
                    resolved.append(best_long)
                elif best_short.confidence_score > best_long.confidence_score + 0.1:
                    resolved.append(best_short)
                else:
                    # Too close to call, skip both or pick higher priority family
                    # For now, let's pick the max
                    resolved.append(max(symbol_ideas, key=lambda x: x.confidence_score))
            else:
                # No direction conflict, pick best confidence per family/subtype if needed
                # Or just pick the single best overall for the symbol
                resolved.append(max(symbol_ideas, key=lambda x: x.confidence_score))
                
        return resolved

    def update_strategies(self, new_strategies: List[BaseStrategy]):
        self.strategies = new_strategies
