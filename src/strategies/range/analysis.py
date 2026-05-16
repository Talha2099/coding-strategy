from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import RegimeType
from src.features.technical_engine import TechnicalFeatureEngine
import numpy as np

from src.core.contracts.strategy_params import RangeParams

class RangeAnalysisEngine:
    """
    ANALYSIS stage for Range / Mean Reversion Trading.
    Answers: Is market tradable range? Is it stable? Center stability?
    """
    def __init__(self):
        pass

    def analyze(self, candles: List[Candle], mtf_state: MTFRegimeState, params: Optional[RangeParams] = None) -> Dict[str, Any]:
        if params is None: params = RangeParams()
        
        ltf_state = mtf_state.ltf_state
        htf_state = mtf_state.htf_state
        regime = RegimeType(ltf_state.regime_type)
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. RANGE TRADABILITY & STRUCTURAL INTEGRITY
        bb_width_norm = features["bb_width"][-1] / (features["bb_mid"][-1] + 1e-9)
        atr_rel = features["atr"][-1] / (features["bb_width"][-1] + 1e-9)
        
        upper_rej = np.mean(features["upper_wick_pct"][-5:])
        lower_rej = np.mean(features["lower_wick_pct"][-5:])
        boundary_quality = (upper_rej + lower_rej) / 2.0
        
        center_stability = 1.0 - min(1.0, abs(features["ema_20"][-1] - features["bb_mid"][-1]) / (features["atr"][-1] + 1e-9))

        # 2. OSCILLATION & VOLATILITY
        hurst = ltf_state.hurst
        is_mean_reverting = hurst < params.min_hurst
        is_compressing = features["bb_squeeze"][-1] > 0.6
        
        # 3. STRATEGIC INTERACTION
        last_high = features["high"][-1]
        last_low = features["low"][-1]
        recent_max = np.max(features["high"][-20:-1])
        recent_min = np.min(features["low"][-20:-1])
        
        is_upper_sweep = (last_high > recent_max) and (features["close"][-1] < recent_max)
        is_lower_sweep = (last_low < recent_min) and (features["close"][-1] > recent_min)
        liquidity_objective = 1 if is_upper_sweep else (-1 if is_lower_sweep else 0)
        
        vol_surge_edge = features["rel_vol"][-1] > 1.6
        body_reversal = (features["close"][-1] < features["open"][-1]) if ltf_state.overextension > 1.5 else \
                        ((features["close"][-1] > features["open"][-1]) if ltf_state.overextension < -1.5 else False)
        
        trap_probability = 0.8 if vol_surge_edge and body_reversal else (0.4 if vol_surge_edge else 0.0)
        value_stability = 1.0 - min(1.0, features["sma_20_slope"][-1] / (features["atr"][-1] + 1e-9))
        
        # 4. HTF ALIGNMENT
        htf_is_rangy = htf_state.regime in [
            RegimeType.RANGE.value, RegimeType.RANGE_ESTABLISHED.value, 
            RegimeType.RANGE_FORMING.value, RegimeType.PRE_TREND_COMPRESSION.value,
            RegimeType.MID_RANGE.value
        ]
        htf_bias_strength = getattr(htf_state, "health_score", 0.5) 
        
        # 4. RANGE HEALTH SCORE (0-1)
        health = (1.0 - hurst) * 0.3 + center_stability * 0.3 + boundary_quality * 0.2 + (1.0 - features["adx"][-1]/params.max_adx) * 0.2
        health = max(0, min(1.0, health))
        
        # 5. BREAKOUT RISK
        # High volume at edges + Bollinger expansion = high risk
        vol_surge = features["rel_vol"][-1] > 1.8
        at_edge = ltf_state.overextension > 1.5 or ltf_state.overextension < -1.5
        # risk from htf trending
        htf_trend_risk = 0.5 if not htf_is_rangy and htf_bias_strength > 0.6 else 0.0
        breakout_risk = (0.3 if is_compressing else 0.0) + (0.3 if vol_surge and at_edge else 0.0) + htf_trend_risk
        breakout_risk = min(1.0, breakout_risk)

        from src.core.utils.logger import system_logger
        system_logger.log_event("RANGE_ANALYSIS_DETAIL", {
            "symbol": ltf_state.symbol,
            "regime": regime.value,
            "health": health,
            "breakout_risk": breakout_risk,
            "hurst": hurst,
            "htf_aligned": htf_is_rangy
        })

        analysis = {
            "regime": regime,
            "is_rangy": regime in [RegimeType.RANGE, RegimeType.RANGE_ESTABLISHED, RegimeType.RANGE_FORMING, RegimeType.MID_RANGE, RegimeType.RANGE_HIGH_TOUCH, RegimeType.RANGE_LOW_TOUCH],
            "is_established": regime in [RegimeType.RANGE_ESTABLISHED, RegimeType.RANGE_HIGH_TOUCH, RegimeType.RANGE_LOW_TOUCH],
            "is_mean_reverting": is_mean_reverting,
            "health": health,
            "breakout_risk": breakout_risk,
            "hurst": hurst,
            "bb_width_norm": bb_width_norm,
            "atr_rel": atr_rel,
            "htf_aligned": htf_is_rangy,
            "is_overextended": abs(ltf_state.overextension) > 2.0,
            "quality_score": health * (1.0 - breakout_risk),
            # Game Theory Metrics
            "trap_probability": trap_probability,
            "liquidity_objective": liquidity_objective, # 1 for lower (short objective), -1 for higher (long objective) - wait, sign check
            "value_stability": value_stability,
            "is_upper_sweep": is_upper_sweep,
            "is_lower_sweep": is_lower_sweep
        }
        return analysis
