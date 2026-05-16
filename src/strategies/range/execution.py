from typing import List, Dict, Any
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine

class RangeExecutionEngine:
    """
    EXECUTE stage for Range / Mean Reversion Trading.
    Handles precise entry: rejection candles, RSI divergence, etc.
    Avoids fading strong momentum breakouts.
    """
    def __init__(self):
        pass

    def check_trigger(self, candles: List[Candle], plan: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        direction = plan["direction"]
        stage = plan.get("stage", "mid")
        
        # 1. BREAKOUT PROTECTION (Refined)
        # If we see price pushing heavily against outer band with expansion, DON'T FADE
        if features["bb_expansion"][-1] > 0.01: # Expanding bands
            return False
            
        # 2. MOMENTUM ADVERSE CHECK
        # Avoid fading into strong momentum (e.g. RSI > 75 for short, or < 25 for long)
        rsi = features["rsi"][-1]
        if direction == -1 and rsi > 78: return False
        if direction == 1 and rsi < 22: return False

        # 3. REJECTION SIGNALS (Stage-aware)
        # Pin bar / Wick rejection
        rej_thresh = 0.35 if stage == "late" else 0.45 # More strict early
        is_upper_rejection = features["upper_wick_pct"][-1] > rej_thresh
        is_lower_rejection = features["lower_wick_pct"][-1] > rej_thresh
        
        # 4. MOMENTUM TURN (Confirmation)
        # Candle close in direction of mean reversion
        # For late stage, we REQUIRE a directional close. For early, maybe just rejection.
        is_closing_reverted = (last.close < last.open) if direction == -1 else (last.close > last.open)
        
        # 5. OVERBOUGHT/OVERSOLD
        is_extreme = (rsi > 65) if direction == -1 else (rsi < 35)

        # 6. STRATEGIC EXECUTION (Game Theory)
        entry_style = plan.get("entry_style", "fade_edge")
        
        # 6a. Trap Reclaim: If we were sweeping, wait for price to close back INSIDE the band
        is_reclaiming = False
        if entry_style == "trap_fade":
             if direction == -1: # Short after upper sweep
                  is_reclaiming = (last.close < features["bb_upper"][-1]) and (features["high"][-2] > features["bb_upper"][-2])
             elif direction == 1: # Long after lower sweep
                  is_reclaiming = (last.close > features["bb_lower"][-1]) and (features["low"][-2] < features["bb_lower"][-2])
        
        # 6b. Absorption: High volume, small body, big rejection wick at edge
        is_absorption = (features["rel_vol"][-1] > 1.8) and (features["body_pct"][-1] < 0.3) and \
                        ((is_upper_rejection if direction == -1 else is_lower_rejection))

        # 7. QUALITY CHECK
        if analysis["quality_score"] < 0.25: return False # Absolute floor

        # 8. FINAL DECISION
        if entry_style == "trap_fade":
             return is_reclaiming or is_absorption
             
        if direction == -1: # Fading High
             return (is_upper_rejection or is_extreme or is_absorption) and is_closing_reverted
        elif direction == 1: # Fading Low
             return (is_lower_rejection or is_extreme or is_absorption) and is_closing_reverted
            
        return False
