from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import RegimeType
from src.features.technical_engine import TechnicalFeatureEngine
import numpy as np

class TrendAnalysisEngine:
    """
    Solves the ANALYZE stage of the Trend Lifecycle.
    Answers: Is there a trend? What stage? Is there persistence?
    """
    def __init__(self):
        pass

    def analyze(self, candles: List[Candle], mtf_state: MTFRegimeState) -> Dict[str, Any]:
        ltf_state = mtf_state.ltf_state
        regime = RegimeType(ltf_state.regime_type)
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Trend Presence & Stage
        is_trending = regime in [
            RegimeType.EARLY_TREND, RegimeType.CONFIRMED_TREND, 
            RegimeType.MID_TREND, RegimeType.LATE_TREND,
            RegimeType.TREND_UP, RegimeType.TREND_DOWN
        ]
        
        # 2. Persistence & Health
        persistence = ltf_state.persistence
        health = ltf_state.health_score
        hurst = ltf_state.hurst
        
        # 3. Alignment Checks
        htf_align = mtf_state.htf_state.direction == ltf_state.direction
        is_pullback = mtf_state.metadata.get("is_pullback", False)
        htf_weakening = mtf_state.metadata.get("htf_weakening", False)

        # 4. Momentum & Acceleration
        acceleration = ltf_state.acceleration
        is_accelerating = acceleration > 0 if ltf_state.direction == 1 else acceleration < 0
        
        # 5. Volatility Regime
        bb_width = features["bb_width"][-1]
        is_compressing = features["bb_squeeze"][-1] > 0.5
        overextension = ltf_state.overextension

        analysis = {
            "regime": regime,
            "direction": ltf_state.direction,
            "is_trending": is_trending,
            "is_new": regime == RegimeType.EARLY_TREND,
            "is_mature": regime == RegimeType.MID_TREND or regime == RegimeType.CONFIRMED_TREND,
            "is_late": regime == RegimeType.LATE_TREND or ltf_state.exhaustion_risk > 0.7,
            "is_exhausted": ltf_state.exhaustion_risk > 0.85 or regime == RegimeType.EXHAUSTION_RISK,
            "overextension": overextension,
            "persistence": persistence,
            "hurst": hurst,
            "health": health,
            "htf_alignment": htf_align,
            "is_pullback_of_htf": is_pullback,
            "htf_weakening": htf_weakening,
            "is_accelerating": is_accelerating,
            "is_compressing": is_compressing,
            "quality_score": (health * 0.4 + persistence * 0.3 + (1.0 if htf_align else 0.5) * 0.3)
        }
        return analysis
