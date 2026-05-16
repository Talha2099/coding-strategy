from typing import List, Dict, Type, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import RegimeType, StrategyFamily, TradeIdea
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.contracts.instrument_registry import InstrumentRegistry

class StrategyRouter:
    """
    Advanced router that activates strategies based on regime, session, and asset class.
    Ranks ideas and suppresses conflicting signals.
    """
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}

    def register_strategy(self, strategy: BaseStrategy):
        self.strategies[strategy.name] = strategy

    def get_trade_ideas(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> List[TradeIdea]:
        if not candles:
            return []
            
        ideas: List[TradeIdea] = []
        spec = InstrumentRegistry.get_spec(symbol)
        last_candle = candles[-1]
        session = InstrumentRegistry.get_session(last_candle.ts, symbol)
        regime = RegimeType(regime_state.regime_type)
        volatility = regime_state.volatility
        
        # 1. Activation & Suppression Logic
        # Trend-specific suppression rules
        is_strong_trend = regime in [
            RegimeType.EARLY_TREND, RegimeType.CONFIRMED_TREND, RegimeType.MID_TREND, 
            RegimeType.TREND_UP, RegimeType.TREND_DOWN, RegimeType.BREAKOUT_ACTIVE,
            RegimeType.CONTINUATION_READY
        ]
        health = getattr(regime_state, "health_score", 0.5)
        
        suppress_mr = is_strong_trend and health > 0.6
        suppress_breakout = (volatility > 0.05 and regime == RegimeType.VOLATILE_UNSTABLE) or \
                            (regime in [RegimeType.RANGE, RegimeType.RANGE_ESTABLISHED] and health < 0.4)
        
        suppress_range = is_strong_trend and health > 0.7
        
        # Only allow pullback continuation in mature trends
        is_mature_trend = regime in [RegimeType.MID_TREND, RegimeType.LATE_TREND, RegimeType.EXHAUSTION_RISK]
        
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
                
            # Special case: Trend Following in Mature stages
            if strategy.family == StrategyFamily.TREND and is_mature_trend:
                # In mature trends, we prefer pullbacks over new breakouts
                # This could be handled inside the strategy itself, but we can hint it here
                pass

            # Technical Setup Detection
            if strategy.detect_setup(candles, regime_state, mtf_state):
                # Check for early invalidation
                if strategy.invalidate_setup(candles, regime_state):
                    continue

                # Trigger Confirmation
                if strategy.confirm_entry(candles, regime_state, mtf_state):
                    idea = strategy.build_trade_idea(symbol, candles, regime_state, mtf_state)
                    if idea:
                        ideas.append(idea)
        
        # 2. Ranking by Adjusted Confidence (Expectancy-based)
        # We rank by Confidence * (TargetDist/StopDist)
        ideas.sort(key=lambda x: x.confidence_score * x.risk_reward_ratio, reverse=True)
        
        # 3. Conflict Resolution (Standard Signal Synthesis)
        # Avoid opposing signals on the same asset
        final_ideas = []
        symbol_map: Dict[str, TradeIdea] = {}
        
        for idea in ideas:
            if idea.symbol not in symbol_map:
                symbol_map[idea.symbol] = idea
            else:
                existing = symbol_map[idea.symbol]
                # If opposite directions, pick the one with significantly higher confidence
                if idea.direction != existing.direction:
                    if idea.confidence_score > existing.confidence_score + 0.15:
                        symbol_map[idea.symbol] = idea
                else:
                    # Same direction, keep the one with better RR or higher confidence
                    if idea.confidence_score * idea.risk_reward_ratio > existing.confidence_score * existing.risk_reward_ratio:
                        symbol_map[idea.symbol] = idea
                        
        return list(symbol_map.values())
