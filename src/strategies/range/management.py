from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, RegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyPhase
from src.features.technical_engine import TechnicalFeatureEngine

class RangeManagementEngine:
    """
    MANAGE/EXIT stage for Range / Mean Reversion Trading.
    Handles: target rotation, breakout exits, range-to-trend transition.
    """
    def __init__(self):
        pass

    def evaluate(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState) -> Optional[Dict[str, Any]]:
        from src.core.contracts.instrument_registry import InstrumentRegistry
        spec = InstrumentRegistry.get_spec(idea.symbol)
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_price = candles[-1].close
        direction = 1 if idea.direction == "long" else -1
        
        updates = {}
        
        # 0. INSTRUMENT-SPECIFIC FAILURE MODES
        behavior = spec.behavior
        if "fake_breakout" in behavior.failure_modes:
            # If we see a strong push above/below edge then immediate reclaim
            if (direction == 1 and features["high"][-1] > features["bb_upper"][-1] and last_price < features["bb_upper"][-1]):
                 # We were long, but it looks like a fake breakout above - exit with caution
                 return {"exit": True, "exit_reason": f"instrument_failure_mode_fake_breakout", "lifecycle_phase": StrategyPhase.EXIT}

        # 1. RANGE BREAKOUT EXIT (Failure) & AUCTION ACCEPTANCE
        # 1a. Hard Breakout
        is_breakout_adverse = (direction == 1 and last_price < features["bb_lower"][-1]) or \
                              (direction == -1 and last_price > features["bb_upper"][-1])
        
        # 1b. Auction Acceptance: Price staying outside or near edge with small candles (acceptance of new value)
        acceptance_adverse = (direction == 1 and features["acceptance_high"][-1] < 0.25) or \
                             (direction == -1 and features["acceptance_high"][-1] > 0.75)
        
        if is_breakout_adverse and (features["bb_expansion"][-1] > 0.02 or acceptance_adverse):
            return {"exit": True, "exit_reason": "range_breakout_or_acceptance", "lifecycle_phase": StrategyPhase.FAILURE}

        # 2. LIQUIDITY OBJECTIVE REACHED
        # If we just swept the opposite side liquidity, we achieved the 'why' of the trade
        recent_max = np.max(features["high"][-20:-1])
        recent_min = np.min(features["low"][-20:-1])
        if direction == 1 and features["high"][-1] > recent_max: # Swept upper while long
             return {"exit": True, "exit_reason": "liquidity_objective_achieved", "lifecycle_phase": StrategyPhase.EXIT}
        elif direction == -1 and features["low"][-1] < recent_min: # Swept lower while short
             return {"exit": True, "exit_reason": "liquidity_objective_achieved", "lifecycle_phase": StrategyPhase.EXIT}

        # 3. RANGE EXHAUSTION / QUALITY Deterioration
        adx = features["adx"][-1]
        hurst = getattr(regime_state, "hurst", 0.5)
        if adx > 28 or hurst > 0.6:
            updates["metadata"] = {**idea.metadata, "exhaustion_risk": True}
            
        # 3. TARGET ROTATION / PARTIAL EXITS
        targets = idea.metadata.get("targets", [])
        if targets:
            # T1 is usually the Mid Line (BB Mid)
            if (direction == 1 and last_price >= targets[0]) or (direction == -1 and last_price <= targets[0]):
                updates["partial_exit"] = 0.5
                updates["stop_loss"] = idea.entry_price # Move to Break-Even
                targets.pop(0)
                updates["metadata"] = {**idea.metadata, "targets": targets, "phase": "mid_range"}
                return updates

        # 4. REGIME SHIFT EXIT
        # If market suddenly enters strong trend (ADX > 32)
        if adx > 32 and (regime_state.direction != direction):
             # Fast exit on trend ignition against us
             return {"exit": True, "exit_reason": "trend_ignition_adverse", "lifecycle_phase": StrategyPhase.EXIT}

        # 5. TRAILING STOP (Only if already past Mid Line)
        if idea.metadata.get("phase") == "mid_range":
             # Trail by 1.5 ATR behind price rotation
             atr = features["atr"][-1]
             trail_sl = last_price - (1.5 * atr) if direction == 1 else last_price + (1.5 * atr)
             if (direction == 1 and trail_sl > idea.stop_loss) or (direction == -1 and (idea.stop_loss == 0 or trail_sl < idea.stop_loss)):
                  updates["stop_loss"] = trail_sl

        return updates if updates else None
