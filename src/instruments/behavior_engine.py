import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine

class BehaviorEngine:
    """
    PHASE 13: Quantitative Instrument-Aware Behavior Engine.
    Converts technical features into behavioral scores [0, 1].
    Used to adjust strategy selection and risk parameters dynamically.
    """
    
    @staticmethod
    def trend_quality_score(features: Dict[str, np.ndarray]) -> float:
        """
        Calculates Trend Quality ∈ [0, 1].
        Inputs: Hurst, ADX, Efficiency, Autocorrelation.
        """
        if "hurst" not in features or "adx" not in features: return 0.5
        
        # 1. Hurst Exponent Contribution (H > 0.5 is trending)
        hurst = features["hurst"][-1]
        h_score = np.clip((hurst - 0.5) / 0.3, 0, 1) # 0.5->0, 0.8->1
        
        # 2. ADX Contribution (ADX > 25 is trending)
        adx = features["adx"][-1]
        adx_score = np.clip((adx - 20) / 40, 0, 1) # 20->0, 60->1
        
        # 3. Efficiency Ratio (Fractal Efficiency)
        eff = features["efficiency"][-1]
        eff_score = np.clip(eff / 0.8, 0, 1) # 0.8->1
        
        # Weighted Combination
        return float(0.4 * h_score + 0.3 * adx_score + 0.3 * eff_score)

    @staticmethod
    def mean_reversion_score(features: Dict[str, np.ndarray]) -> float:
        """
        Calculates Mean Reversion Propensity ∈ [0, 1].
        High score means price is likely to revert.
        """
        if "hurst" not in features or "zscore" not in features: return 0.5
        
        # 1. Hurst (H < 0.5 is anti-persistent/mean reverting)
        hurst = features["hurst"][-1]
        h_score = np.clip((0.5 - hurst) / 0.3, 0, 1) # 0.5->0, 0.2->1
        
        # 2. Statistical Stretch (Z-score)
        z = abs(features["zscore"][-1])
        z_score = np.clip((z - 1.5) / 1.5, 0, 1) # 1.5->0, 3.0->1
        
        # 3. Variance Ratio (Simplified proxy: BB width stability)
        # If BB are expanding, MR is weaker
        bb_exp = features["bb_expansion"][-1]
        bb_score = 1.0 - np.clip(bb_exp * 10, 0, 1) 
        
        return float(0.4 * h_score + 0.4 * z_score + 0.2 * bb_score)

    @staticmethod
    def breakout_quality_score(features: Dict[str, np.ndarray]) -> float:
        """
        Calculates the quality of a potential breakout ∈ [0, 1].
        """
        if "rel_vol" not in features or "bb_width" not in features: return 0.0
        
        # 1. Volatility Expansion
        rel_vol = features["rel_vol"][-1]
        vol_score = np.clip((rel_vol - 1.2) / 2.0, 0, 1) # 1.2->0, 3.2->1
        
        # 2. Range Compression (Squeeze before breakout)
        bbw = features["bb_width"][-1]
        bbw_avg = np.mean(features["bb_width"][-20:])
        squeeze_score = np.clip((bbw_avg / (bbw + 1e-9)) - 1.0, 0, 1)
        
        # 3. Displacement (Size of move relative to ATR)
        # Assuming last returns exist
        ret = abs(features["returns"][-1])
        atr = features["atr"][-1]
        price = features["close"][-1]
        disp_score = np.clip((ret * price) / (atr + 1e-9), 0, 1)
        
        return float(0.4 * vol_score + 0.3 * squeeze_score + 0.3 * disp_score)

    @staticmethod
    def fake_breakout_probability(features: Dict[str, np.ndarray]) -> float:
        """
        Probability of a fakeout ∈ [0, 1].
        Based on wick rejection and low volume follow-through.
        """
        if "upper_wick_pct" not in features: return 0.5
        
        # 1. Wick Rejection
        upper_wick = features["upper_wick_pct"][-1]
        lower_wick = features["lower_wick_pct"][-1]
        max_wick = max(upper_wick, lower_wick)
        wick_score = np.clip((max_wick - 0.3) / 0.4, 0, 1) # 0.3->0, 0.7->1
        
        # 2. Volume Anomaly (Breakout on low relative volume)
        rel_vol = features["rel_vol"][-1]
        vol_score = 1.0 - np.clip(rel_vol / 1.5, 0, 1) # rel_vol > 1.5 -> low probability of fakeout
        
        # 3. Distance from Mean
        z = abs(features["zscore"][-1])
        overextended_score = np.clip((z - 2.5) / 1.5, 0, 1) # z>2.5 is risky
        
        return float(0.5 * wick_score + 0.2 * vol_score + 0.3 * overextended_score)

    @staticmethod
    def volatility_regime_score(features: Dict[str, np.ndarray]) -> float:
        """
        Current volatility intensity ∈ [0, 1].
        """
        # Using vol_regime from TechnicalFeatureEngine as base (0, 1, 2)
        # mapped to 0.2, 0.5, 0.8
        base = features["vol_regime"][-1]
        if base == 0: return 0.2
        if base == 1: return 0.5
        return 0.8

    @staticmethod
    def liquidity_event_score(features: Dict[str, np.ndarray]) -> float:
        """
        Detects potential liquidity sweeps or absorption ∈ [0, 1].
        """
        # Exhaustion score from tech engine
        exhaustion = features.get("exhaustion_score", np.zeros(1))[-1]
        
        # Acceptance check
        acceptance = features.get("acceptance_high", np.zeros(1))[-1]
        
        # If high exhaustion and low acceptance of the extreme level -> high sweep prob
        sweep_prob = np.clip(exhaustion * (1.1 - acceptance), 0, 1)
        return float(sweep_prob)

    @classmethod
    def get_behavior_profile(cls, candles: List[Candle], symbol: Optional[str] = None) -> Dict[str, float]:
        features = TechnicalFeatureEngine.get_candle_features(candles, symbol)
        if not features:
            return {
                "trend_quality": 0.5,
                "mean_reversion": 0.5,
                "breakout_quality": 0.0,
                "fake_breakout_prob": 0.5,
                "volatility_intensity": 0.5,
                "liquidity_event": 0.0
            }
            
        return {
            "trend_quality": cls.trend_quality_score(features),
            "mean_reversion": cls.mean_reversion_score(features),
            "breakout_quality": cls.breakout_quality_score(features),
            "fake_breakout_prob": cls.fake_breakout_probability(features),
            "volatility_intensity": cls.volatility_regime_score(features),
            "liquidity_event": cls.liquidity_event_score(features)
        }
