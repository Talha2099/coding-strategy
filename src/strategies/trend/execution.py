from typing import List, Dict, Any
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine

class TrendExecutionEngine:
    """
    Solves the EXECUTE stage of the Trend Lifecycle.
    Handles precise entry timing (breakout triggers, pullback reversals).
    """
    def __init__(self):
        pass

    def check_trigger(self, candles: List[Candle], plan: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        direction = analysis["direction"]
        entry_style = plan["entry_style"]
        
        # 1. GLOBAL EXECUTION GUARDS
        
        # A. Session Context (Optional: restrict to liquid sessions 2=London, 3=NY)
        # 1=Asia, 4=Late US, 0=Weekend/Other
        # for now just avoid 0/4 if looking for high volume breakouts
        curr_session = features["session_labels"][-1]
        if entry_style == "breakout" and curr_session in [0, 4]:
            return False
            
        # B. Volatility Integrity
        # 2.0 = High Vol Spike, 0.0 = Dead. We want 1.0 (Normal Trending) or 2.0 if breakout
        vol_regime = features["vol_regime"][-1]
        if vol_regime == 0.0: return False # No interest
        
        # C. Momentum Confirmation
        rel_vol = features["rel_vol"][-1]
        if entry_style == "breakout" and rel_vol < 1.0:
            return False # Breakout with no volume is a fakeout
            
        # D. Technical Guards
        if direction == 1 and features["rsi"][-1] > 78: return False # Too hot
        if direction == -1 and features["rsi"][-1] < 22: return False # Too cold
        
        # 2. REGIME-AWARE TIMING
        if entry_style == "breakout":
            # Must break out of local range with volume/momentum
            has_new_peak = features["is_hh"][-1] > 0 or features["is_ll"][-1] > 0
            is_strong = features["body_pct"][-1] > 0.5
            return has_new_peak and is_strong
            
        elif entry_style == "pullback":
            # Acceptance at mean confirmation
            acceptance = features["acceptance_high"][-1]
            # If long, we want acceptance to be high (closing at top of ranges)
            is_valid_acceptance = acceptance > 0.6 if direction == 1 else acceptance < 0.4
            
            if direction == 1:
                return last.close > candles[-2].high and last.close > last.open and is_valid_acceptance
            else:
                return last.close < candles[-2].low and last.close < last.open and not is_valid_acceptance
                
        elif entry_style == "continuation":
            # Momentum trigger: closing in outer third of candle
            body_range = abs(last.close - last.open)
            total_range = last.high - last.low + 1e-9
            is_strong = body_range / total_range > 0.6
            return is_strong and (last.close > last.open if direction == 1 else last.close < last.open)
            
        return False
