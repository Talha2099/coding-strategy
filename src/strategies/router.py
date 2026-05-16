from typing import List, Optional, Dict, Any
import numpy as np
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.strategies.base import BaseStrategy
from src.core.contracts.instrument_registry import InstrumentRegistry

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
        spec = InstrumentRegistry.get_spec(symbol)
        
        # 1. Filter active strategies for this regime AND instrument
        active_strats = []
        for s in self.strategies:
            if not s.is_valid_regime(current_regime):
                continue
            
            # Instrument-specific restriction
            if s.name in spec.restricted_strategies:
                continue
            
            active_strats.append(s)
        
        # 2. Collect setup detection results
        ideas: List[TradeIdea] = []
        for strat in active_strats:
            if strat.detect_setup(candles, regime_state, mtf_state):
                if strat.confirm_entry(candles):
                    idea = strat.build_trade_idea(symbol, candles, regime_state, mtf_state)
                    if idea:
                        # 2.1 Strategic Alignement Scoring
                        alignment_boost = self._calculate_alignment_boost(idea, spec, regime_state, candles)
                        idea = self._apply_boost(idea, alignment_boost)
                        ideas.append(idea)
                        
        # 3. Suppress conflicting ideas (e.g. Long vs Short in same asset class)
        final_ideas = self._resolve_conflicts(ideas)
        
        # 4. Rank candidates by boosted confidence score
        final_ideas.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return final_ideas

    def _calculate_alignment_boost(self, idea: TradeIdea, spec: any, regime_state: RegimeState, candles: List[Candle]) -> float:
        """Calculates a confidence multiplier based on instrument 'DNA', Strategy Matrix, and Behavioral Engine"""
        from src.core.contracts.strategy_matrix import StrategyCompatibilityMatrix
        from src.core.contracts.instrument_spec import SessionType
        from src.scoring.behavioral_validation import BehavioralValidator
        
        # 1. Base Strategy Matrix Score
        session = SessionType.NEW_YORK # Default for now
        matrix_score = StrategyCompatibilityMatrix.get_suitability_score(
            strategy_family=idea.strategy_family,
            archetype=spec.behavior.archetype,
            regime=RegimeType(regime_state.regime_type),
            session=session,
            volatility=getattr(regime_state, "volatility", 0.2),
            trend_strength=getattr(regime_state, "trend_strength", 0.5)
        )
        
        boost = 0.5 + matrix_score 
        
        # 2. Preferred Strategy Overrides
        if idea.strategy_name in spec.preferred_strategies:
            boost += 0.1
            
        # 3. PHASE 13: Behavioral Engine & Validation Integration
        is_aligned, behavior_score, reason = BehavioralValidator.validate_behavioral_alignment(
            idea, candles, regime_state
        )
        
        if not is_aligned:
            # Significant penalty but don't hard block here (let router/risk engine decide)
            boost *= 0.3
        else:
            # Map behavior score [0,1] to a [0.8, 1.3] multiplier
            behavior_boost = 0.8 + (behavior_score * 0.5)
            boost *= behavior_boost
            
        return max(0.1, min(3.0, boost))

    def _apply_boost(self, idea: TradeIdea, boost: float) -> TradeIdea:
        # We can't actually modify TradeIdea if it's frozen=True, 
        # but in strategy.py it is frozen=True. 
        # I'll update the metadata and score in a new instance.
        from dataclasses import replace
        new_score = min(1.0, idea.confidence_score * boost)
        return replace(idea, confidence_score=new_score, metadata={**idea.metadata, "alignment_boost": boost})

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
