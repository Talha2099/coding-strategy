from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, RegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyPhase
from src.features.technical_engine import TechnicalFeatureEngine

class TrendManagementEngine:
    """
    Solves the MANAGE and EXIT stages of the Trend Lifecycle.
    Handles trailing stops, partial profits, and dynamic exits based on trend health.
    """
    def __init__(self):
        pass

    def evaluate(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState) -> Optional[Dict[str, Any]]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_price = candles[-1].close
        direction = 1 if idea.direction == "long" else -1
        
        # 1. MONITOR TREND HEALTH & EXHAUSTION
        health = regime_state.health_score
        exhaustion = regime_state.exhaustion_risk
        acceleration = regime_state.acceleration
        hurst = regime_state.hurst
        
        updates = {}
        
        # 2. EMERGENCY EXIT GUARDS
        # A. Trend Integrity Failure
        failed_regimes = [RegimeType.TREND_FAILED.value, RegimeType.REVERSAL_RISK.value, RegimeType.VOLATILE_UNSTABLE.value]
        if regime_state.regime_type in failed_regimes:
            return {"exit": True, "exit_reason": "regime_shift_failure", "lifecycle_phase": StrategyPhase.EXIT}
            
        if health < 0.2:
             return {"exit": True, "exit_reason": "health_collapse", "lifecycle_phase": StrategyPhase.EXIT}

        # B. Reversal Spike / Abnormal Volatility
        vol_regime = features["vol_regime"][-1]
        if vol_regime == 2.0 and acceleration * direction < -0.0005:
             # High volatility reversal attempt
             return {"exit": True, "exit_reason": "reversal_vol_spike", "lifecycle_phase": StrategyPhase.EXIT}

        # C. Persistence Loss
        if hurst < 0.4 and health < 0.4:
             return {"exit": True, "exit_reason": "persistence_loss_stagnation", "lifecycle_phase": StrategyPhase.EXIT}

        # 3. DYNAMIC TRAILING & BREAK-EVEN
        atr = features["atr"][-1]
        
        # Distances
        dist_from_entry = (last_price - idea.entry_price) * direction
        rr_to_sl = abs(idea.entry_price - idea.stop_loss)
        
        # A. Break-Even Trigger (Move to BE when 1:1 risk/reward reached)
        is_be = idea.stop_loss == idea.entry_price
        if not is_be and dist_from_entry > rr_to_sl:
             updates["stop_loss"] = idea.entry_price
             
        # B. Advanced Trailing
        # Tighten as trend matures or exhausts
        is_late = regime_state.regime_type == RegimeType.LATE_TREND.value or exhaustion > 0.6
        is_exhausted = regime_state.regime_type == RegimeType.EXHAUSTION_RISK.value or exhaustion > 0.85
        
        if is_exhausted:
            proposed_sl = last_price - (atr * 1.0 * direction) # super tight
        elif is_late:
            proposed_sl = last_price - (atr * 1.5 * direction) # tight
        else:
            # Healthy trend trailing (EMA 20 or Chandelier-style)
            proposed_sl = features["ema_20"][-1] - (atr * 0.5 * direction)
            
        # Ensure stop only moves in profit direction
        current_sl = updates.get("stop_loss", idea.stop_loss)
        if direction == 1:
            if proposed_sl > current_sl:
                updates["stop_loss"] = proposed_sl
        else:
            if proposed_sl < current_sl:
                updates["stop_loss"] = proposed_sl
                
        # 4. PARTIAL PROFITS & SCALE OUT
        if "targets" in idea.metadata:
            targets = idea.metadata["targets"]
            if targets and ((direction == 1 and last_price >= targets[0]) or (direction == -1 and last_price <= targets[0])):
                updates["partial_exit"] = 0.5 # Exit half
                targets.pop(0)
                updates["metadata"] = {**idea.metadata, "targets": targets}
                
        # 5. HOLDING THROUGH PULLBACKS
        # Logic: if health > 0.6 and persistence > 0.6, we ignore minor stop tighter signals
        # Or if regime is PULLBACK_IN_TREND but health is stable
        if regime_state.regime_type == RegimeType.PULLBACK_IN_TREND.value and health > 0.5:
             # Don't tighten stop during valid pullbacks, use original wide trailing
             pass

        return updates if updates else None
