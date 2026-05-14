from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, MTFRegimeState
from src.core.types.strategy import RegimeType, StrategyPhase
from src.features.technical_engine import TechnicalFeatureEngine

class RangePlanningEngine:
    """
    PLAN stage for Range / Mean Reversion Trading.
    Decides: fade edge? which edge? profit targets (mean or opposite edge)?
    """
    def __init__(self, min_width_atr: float = 2.0):
        self.min_width_atr = min_width_atr

    def plan(self, candles: List[Candle], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # 1. NO-TRADE LOGIC (Explicit Rejection Reasons)
        rejection_reason = None
        
        if not analysis["is_rangy"] and not analysis["is_overextended"]:
            rejection_reason = "not_in_range_or_mean_reversion_context"
        elif analysis["health"] < 0.25:
            rejection_reason = "range_health_too_low"
        elif analysis["atr_rel"] > 0.7:
            rejection_reason = "range_too_noisy"
        elif analysis["bb_width_norm"] < 0.0015:
            rejection_reason = "range_too_narrow"
        elif analysis["breakout_risk"] > 0.7 and not analysis["is_overextended"]:
            rejection_reason = "breakout_risk_too_high"
            
        if rejection_reason:
            from src.core.utils.logger import system_logger
            system_logger.log_event("RANGE_PLAN_REJECTED", {
                "reason": rejection_reason,
                "analysis_health": analysis["health"]
            })
            # We skip this setup
            return None

        # 2. LIFECYCLE STAGE CLASSIFICATION
        # Early: fresh range forming, high rejection quality
        # Mid: established range, high center stability
        # Late: mature range, high breakout risk or time spent
        stage = "mid"
        if analysis["regime"] == RegimeType.RANGE_FORMING:
            stage = "early"
        elif analysis["regime"] == RegimeType.RANGE_ESTABLISHED and analysis["health"] > 0.7:
            stage = "mid"
        elif analysis["breakout_risk"] > 0.4:
            stage = "late"

        # 3. SELECTION OF FADE EDGE
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_price = candles[-1].close
        bb_upper = features["bb_upper"][-1]
        bb_lower = features["bb_lower"][-1]
        bb_mid = features["bb_mid"][-1]
        
        direction = 0
        entry_style = "fade_edge"
        
        # Distance to boundaries
        dist_to_upper = bb_upper - last_price
        dist_to_lower = last_price - bb_lower
        
        if dist_to_upper < (bb_upper - bb_mid) * 0.25:
             direction = -1 # Fade High
        elif dist_to_lower < (bb_mid - bb_lower) * 0.25:
             direction = 1 # Fade Low
        elif analysis["is_overextended"]:
             direction = -1 if last_price > bb_mid else 1
             entry_style = "mean_reversion"
        else:
             return None # Mid-range rotation, no clear edge

        # 4. CALCULATE LEVELS & RISK
        atr = features["atr"][-1]
        
        # Stop distance scales with volatility and breakout risk
        stop_dist = atr * (1.5 + analysis["breakout_risk"])
        invalidation = bb_upper + stop_dist if direction == -1 else bb_lower - stop_dist
        
        # Targets
        target_mid = bb_mid
        target_opp = bb_lower if direction == -1 else bb_upper
        
        # Risk adjustment by stage
        risk_mult = 1.0
        if stage == "late": risk_mult = 0.5 # De-risk late range
        elif stage == "early": risk_mult = 0.8 # De-risk unconfirmed range
        
        # Risk-Reward Gate
        risk = abs(last_price - invalidation)
        reward = abs(last_price - target_mid)
        if reward / (risk + 1e-9) < 0.7:
             return None

        return {
            "entry_style": entry_style,
            "stage": stage,
            "direction": direction,
            "invalidation": invalidation,
            "stop_loss": invalidation,
            "targets": [target_mid, target_opp],
            "risk_pct": 0.01 * analysis["quality_score"] * risk_mult,
            "phase": StrategyPhase.PLANNING,
            "metadata": {
                "is_mean_reversion": entry_style == "mean_reversion",
                "range_health": analysis["health"],
                "breakout_risk": analysis["breakout_risk"],
                "range_stage": stage,
                "trailing_rule": "atr_1.5_after_midpoint",
                "scale_plan": "partial_50_at_midpoint"
            }
        }
