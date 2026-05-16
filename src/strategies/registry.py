from typing import List, Dict, Type, Optional, Tuple
from src.strategies.base import BaseStrategy
from src.core.types.strategy import RegimeType, StrategyFamily, TradeIdea
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.contracts.instrument_registry import InstrumentRegistry
from src.instruments.behavior_engine import BehaviorEngine
from src.scoring.behavioral_validation import BehavioralValidator

class StrategyRouter:
    """
    PHASE 13: Dynamic Behavior-Aware Strategy Router.
    Prioritizes and activates strategies based on Quantitative Behavior Scores.
    """
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}

    def register_strategy(self, strategy: BaseStrategy):
        self.strategies[strategy.name] = strategy

    def dynamic_strategy_router(self, symbol: str, candles: List[Candle], regime_state: RegimeState) -> Dict[StrategyFamily, float]:
        """
        Logic for dynamic allocation based on behavior scores.
        """
        scores = BehaviorEngine.get_behavior_profile(candles, symbol)
        
        allocations = {
            StrategyFamily.TREND: scores["trend_quality"],
            StrategyFamily.BREAKOUT: scores["breakout_quality"],
            StrategyFamily.MEAN_REVERSION: scores["mean_reversion"],
            StrategyFamily.RANGE: 1.0 - scores["trend_quality"] # Range inverse of trend quality
        }
        
        # Adjust for fake breakout probability
        if scores["fake_breakout_prob"] > 0.6:
            allocations[StrategyFamily.BREAKOUT] *= 0.5
            
        return allocations

    def get_trade_ideas(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> List[TradeIdea]:
        if not candles:
            return []
            
        ideas: List[TradeIdea] = []
        spec = InstrumentRegistry.get_spec(symbol)
        last_candle = candles[-1]
        
        # Get Dynamic Behavioral Allocations
        allocations = self.dynamic_strategy_router(symbol, candles, regime_state)
        
        regime = RegimeType(regime_state.regime_type)
        volatility = regime_state.volatility
        
        # 1. Activation & Suppression Logic
        is_strong_trend = regime in [
            RegimeType.EARLY_TREND, RegimeType.CONFIRMED_TREND, RegimeType.MID_TREND, 
            RegimeType.TREND_UP, RegimeType.TREND_DOWN, RegimeType.BREAKOUT_ACTIVE,
            RegimeType.CONTINUATION_READY
        ]
        health = getattr(regime_state, "health_score", 0.5)
        
        # Enhanced suppression using Behavioral Scores
        scores = BehaviorEngine.get_behavior_profile(candles, symbol)
        
        suppress_mr = is_strong_trend and health > 0.6 and scores["trend_quality"] > 0.7
        suppress_breakout = (volatility > 0.05 and regime == RegimeType.VOLATILE_UNSTABLE) or \
                            (scores["fake_breakout_prob"] > 0.75)
        
        suppress_range = is_strong_trend and health > 0.7
        
        for name, strategy in self.strategies.items():
            # Regime Filtering
            if not strategy.is_valid_regime(regime):
                continue
                
            # Family Suppression
            if strategy.family == StrategyFamily.MEAN_REVERSION and suppress_mr:
                continue
            if strategy.family == StrategyFamily.RANGE and (suppress_mr or suppress_range):
                continue
            if strategy.family == StrategyFamily.BREAKOUT and suppress_breakout:
                continue
                
            # Behavioral Allocation Check
            # If the quantitative score for this family is very low, skip to reduce noise
            if allocations.get(strategy.family, 1.0) < 0.2:
                continue

            # Technical Setup Detection
            if strategy.detect_setup(candles, regime_state, mtf_state):
                # Check for early invalidation
                if strategy.invalidate_setup(candles, regime_state):
                    continue

                # Trigger Confirmation
                if strategy.confirm_entry(candles, regime_state, mtf_state):
                    idea = strategy.build_trade_idea(symbol, candles, regime_state, mtf_state)
                    if idea:
                        # PHASE 13: Behavior-Aware Execution Modifications
                        b_scores = BehaviorEngine.get_behavior_profile(candles, symbol)
                        
                        # 4.1 Volatility Adjustment (Widen Stops)
                        if b_scores["volatility_intensity"] > 0.7:
                            # Modify Idea: Widen SL by 20%
                            from dataclasses import replace
                            new_sl_dist = abs(idea.entry_price - idea.stop_loss) * 1.2
                            new_sl = idea.entry_price - new_sl_dist if idea.direction == "long" else idea.entry_price + new_sl_dist
                            idea = replace(idea, stop_loss=new_sl, metadata={**idea.metadata, "vol_stop_widening": True})

                        # 4.2 Liquidity Confirmation delay (Simulated by reducing confidence if no sweep yet)
                        if b_scores["liquidity_event"] > 0.8:
                            # Requires confirmation -> reduce confidence until it happens
                            # If it's a breakout but we suspect a sweep is happening
                            idea = replace(idea, confidence_score=idea.confidence_score * 0.9, metadata={**idea.metadata, "liquidity_wait_penalty": True})

                        # Apply behavioral boost in router
                        alignment_boost = self._calculate_alignment_boost(idea, spec, regime_state, candles)
                        # factor in dynamic allocation
                        idea.confidence_score *= (0.8 + allocations.get(idea.strategy_family, 1.0) * 0.4)
                        ideas.append(idea)
        
        # 2. Ranking by Adjusted Confidence (Expectancy-based)
        ideas.sort(key=lambda x: x.confidence_score * x.risk_reward_ratio, reverse=True)
        
        # 3. Conflict Resolution
        final_ideas = []
        symbol_map: Dict[str, TradeIdea] = {}
        
        for idea in ideas:
            if idea.symbol not in symbol_map:
                symbol_map[idea.symbol] = idea
            else:
                existing = symbol_map[idea.symbol]
                if idea.direction != existing.direction:
                    if idea.confidence_score > existing.confidence_score + 0.15:
                        symbol_map[idea.symbol] = idea
                else:
                    if idea.confidence_score * idea.risk_reward_ratio > existing.confidence_score * existing.risk_reward_ratio:
                        symbol_map[idea.symbol] = idea
                        
        return list(symbol_map.values())

    def _calculate_alignment_boost(self, idea: TradeIdea, spec: any, regime_state: RegimeState, candles: List[Candle]) -> float:
        """Calculates a confidence multiplier based on YAML priors and Behavior scores."""
        from src.core.contracts.strategy_matrix import StrategyCompatibilityMatrix
        from src.core.contracts.instrument_spec import SessionType
        from src.scoring.behavioral_validation import BehavioralValidator
        
        session = SessionType.NEW_YORK 
        matrix_score = StrategyCompatibilityMatrix.get_suitability_score(
            strategy_family=idea.strategy_family,
            archetype=spec.behavior.archetype,
            session=session,
            volatility=getattr(regime_state, "volatility", 0.2),
            trend_strength=getattr(regime_state, "trend_strength", 0.5)
        )
        
        boost = 0.5 + matrix_score 
        
        if idea.strategy_name in spec.preferred_strategies:
            boost *= 1.2
            
        # Behavioral Validator integration
        is_aligned, behavior_score, reason = BehavioralValidator.validate_behavioral_alignment(
            idea, candles, regime_state
        )
        
        if not is_aligned:
            boost *= 0.3
        else:
            behavior_boost = 0.8 + (behavior_score * 0.5)
            boost *= behavior_boost
            
        return max(0.1, min(3.0, boost))
