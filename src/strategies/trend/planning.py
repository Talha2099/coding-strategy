from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, MTFRegimeState
from src.core.types.strategy import RegimeType, StrategyPhase
from src.features.technical_engine import TechnicalFeatureEngine

class TrendPlanningEngine:
    """
    Solves the PLAN stage of the Trend Lifecycle.
    Decides entry style, invalidation, targets, and risk profile.
    """
    def __init__(self, atr_mult_stop: float = 2.0, reward_ratio: float = 2.0):
        self.atr_mult_stop = atr_mult_stop
        self.reward_ratio = reward_ratio

    def plan(self, candles: List[Candle], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # NO-TRADE LOGIC
        if not analysis["is_trending"] and not analysis["is_compressing"]:
            return None
            
        if analysis["is_exhausted"]:
            return None # Late trend protection
            
        if analysis["is_late"] and not analysis["is_pullback_of_htf"]:
             # Don't chase late trends unless it's a pullback setup
             return None

        if analysis["health"] < 0.4:
            return None # Low quality trend
            
        # WAIT FOR PULLBACK LOGIC
        if self.should_wait_for_pullback(analysis):
            # We return None or a special "WAIT" state if we want to signal it, 
            # but for now, we reject the setup as "not ready".
            return None

        # ENTRY STYLE SELECTION
        entry_style = "continuation"
        order_type = "MARKET" # Default
        
        if analysis["is_new"] or analysis["is_compressing"]:
            entry_style = "breakout"
            order_type = "STOP"
        elif analysis["is_pullback_of_htf"] or analysis["regime"] == RegimeType.PULLBACK_IN_TREND:
            entry_style = "pullback"
            order_type = "LIMIT"
            
        # CALCULATE LEVELS
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        last_price = candles[-1].close
        direction = analysis["direction"]
        
        # Invalidation & Stop
        # Pullbacks get tighter stops, breakouts need more room
        stop_mult = self.atr_mult_stop
        if entry_style == "pullback": stop_mult = 1.5
        elif entry_style == "breakout": stop_mult = 2.5
        
        stop_dist = atr * stop_mult
        invalidation = last_price - (stop_dist * direction)
        
        # Targets
        target_1 = last_price + (stop_dist * direction * self.reward_ratio)
        target_2 = last_price + (stop_dist * direction * self.reward_ratio * 2.0)
        
        # Risk Scaling
        # More persistence = more risk allowed
        base_risk = 0.01
        risk_scalar = analysis["quality_score"]
        if analysis["is_late"]: risk_scalar *= 0.5 # De-risk late stage
        
        plan = {
            "entry_style": entry_style,
            "order_type": order_type,
            "invalidation": invalidation,
            "stop_loss": invalidation,
            "targets": [target_1, target_2],
            "risk_pct": base_risk * risk_scalar,
            "phase": StrategyPhase.PLANNING,
            "metadata": {
                "entry_type": entry_style,
                "order_type": order_type,
                "analysis_quality": analysis["quality_score"],
                "is_pullback": entry_style == "pullback"
            }
        }
        return plan

    def should_wait_for_pullback(self, analysis: Dict[str, Any]) -> bool:
        """Rule: if trend is mature but overextended, wait for pullback."""
        if analysis["is_mature"] or analysis["is_late"]:
             # If too far from mean, don't chase
             if analysis.get("overextension", 0.0) > 2.0:
                  return True
        return False
