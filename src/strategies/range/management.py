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
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_price = candles[-1].close
        direction = 1 if idea.direction == "long" else -1
        
        updates = {}
        
        # 1. RANGE BREAKOUT EXIT (Failure)
        # If price closes outside the opposite edge of the range with expansion
        is_breakout_adverse = (direction == 1 and last_price < features["bb_lower"][-1]) or \
                              (direction == -1 and last_price > features["bb_upper"][-1])
        
        if is_breakout_adverse and features["bb_expansion"][-1] > 0.02:
            return {"exit": True, "exit_reason": "range_breakout_confirmed", "lifecycle_phase": StrategyPhase.FAILURE}

        # 2. RANGE EXHAUSTION / QUALITY Deterioration
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
