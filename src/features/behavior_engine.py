import numpy as np
from typing import Dict, List, Optional
from src.core.types.trading import Candle

class BehaviorFeatureEngine:
    """
    STAGE F: Behavioral Scores.
    Converts features into probabilistic behavioral mappings [0, 1].
    """
    
    @staticmethod
    def extract(all_features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        if not all_features: return {}
        
        # Helper to get features safely
        f = all_features
        length = len(f.get("close", []))
        if length == 0: return {}

        # 1. Trend Quality Score
        hurst = f.get("hurst", np.full(length, 0.5))
        adx = f.get("adx", np.zeros(length))
        efficiency = f.get("efficiency", np.full(length, 0.5))
        
        h_score = np.clip((hurst - 0.5) / 0.3, 0, 1)
        adx_score = np.clip((adx - 20) / 40, 0, 1)
        eff_score = np.clip(efficiency / 0.8, 0, 1)
        
        trend_quality = 0.4 * h_score + 0.3 * adx_score + 0.3 * eff_score
        
        # 2. Mean Reversion Score
        zscore = f.get("zscore", np.zeros(length))
        bb_expansion = f.get("bb_expansion", np.zeros(length))
        
        mr_h_score = np.clip((0.5 - hurst) / 0.3, 0, 1)
        mr_z_score = np.clip((np.abs(zscore) - 1.5) / 1.5, 0, 1)
        mr_bb_score = 1.0 - np.clip(bb_expansion * 10, 0, 1)
        
        mean_reversion = 0.4 * mr_h_score + 0.4 * mr_z_score + 0.2 * mr_bb_score
        
        # 3. Fake Breakout Probability
        upper_wick = f.get("upper_wick_pct", np.zeros(length))
        lower_wick = f.get("lower_wick_pct", np.zeros(length))
        max_wick = np.maximum(upper_wick, lower_wick)
        rel_vol = f.get("rel_vol", np.ones(length))
        
        wick_score = np.clip((max_wick - 0.3) / 0.4, 0, 1)
        fake_vol_score = 1.0 - np.clip(rel_vol / 1.5, 0, 1)
        overextended_score = np.clip((np.abs(zscore) - 2.5) / 1.5, 0, 1)
        
        fake_breakout_prob = 0.5 * wick_score + 0.2 * fake_vol_score + 0.3 * overextended_score
        
        # 4. Breakout Quality
        bb_squeeze = f.get("bb_squeeze", np.zeros(length))
        breakout_vol = np.clip((rel_vol - 1.2) / 2.0, 0, 1)
        breakout_displacement = f.get("displacement", np.zeros(length))
        
        breakout_quality = 0.4 * breakout_vol + 0.3 * bb_squeeze + 0.3 * breakout_displacement
        
        # 5. Reversal Risk
        dist_ema20 = f.get("dist_ema20", np.zeros(length))
        exhaustion = f.get("exhaustion_score", np.zeros(length))
        reversal_risk = 0.6 * exhaustion + 0.4 * np.clip((np.abs(dist_ema20) - 3.0) / 2.0, 0, 1)
        
        # 6. Compression / Expansion
        bb_width = f.get("bb_width", np.zeros(length))
        bb_expansion = f.get("bb_expansion", np.zeros(length))
        compression_score = 1.0 - np.clip((bb_width - np.percentile(bb_width, 10)) / (np.percentile(bb_width, 50) - np.percentile(bb_width, 10) + 1e-9), 0, 1)
        expansion_score = np.clip(bb_expansion * 50, 0, 1) # Normalized expansion
        
        # 7. Persistence and Maturity
        time_in_trend = f.get("time_in_trend", np.zeros(length))
        persistence = np.clip(time_in_trend / 20.0, 0, 1) # Relative to a 20-bar lookback
        maturity = np.clip(time_in_trend / 100.0, 0, 1) # Longer horizon maturity
        
        # 8. Range Stability
        range_width = f.get("kc_width", np.zeros(length))
        range_stability = (1.0 - np.clip(np.abs(pd.Series(range_width).diff().values * 100), 0, 1)) * (1.0 - np.clip(np.abs(zscore)/4.0, 0, 1))

        # 9. Volatility Intensity
        realized_vol = f.get("realized_vol", np.zeros(length))
        vol_regime = f.get("vol_regime", np.ones(length))
        volatility_intensity = np.clip(realized_vol / (pd.Series(realized_vol).rolling(100).mean().values + 1e-9), 0, 2) / 2.0
        volatility_intensity = 0.7 * volatility_intensity + 0.3 * (vol_regime / 2.0)

        # 10. Liquidity Event Score
        upside_sweep = f.get("upside_sweep", np.zeros(length))
        downside_sweep = f.get("downside_sweep", np.zeros(length))
        liquidity_event = np.maximum(upside_sweep, downside_sweep)
        liquidity_event_score = 0.8 * liquidity_event + 0.2 * np.clip(rel_vol / 2.0, 0, 1)

        # 11. Continuation Score
        # High when we just had a pullback (Stage 5 in lifecycle) that is resolving
        trend_lifecycle = f.get("trend_lifecycle", np.zeros(length))
        continuation_score = np.where(trend_lifecycle == 5.0, 0.8, 0.0) # Pullback phase
        continuation_score = np.where((pd.Series(trend_lifecycle).shift(1) == 5.0) & (returns * ema_cross > 0), 1.0, continuation_score)

        return {
            "trend_quality_score": trend_quality,
            "mean_reversion_score": mean_reversion,
            "fake_breakout_prob": fake_breakout_prob,
            "breakout_quality_score": breakout_quality,
            "reversal_risk_score": reversal_risk,
            "compression_score": compression_score,
            "expansion_score": expansion_score,
            "persistence_score": persistence,
            "regime_maturity": maturity,
            "range_stability_score": range_stability,
            "volatility_intensity_score": volatility_intensity,
            "liquidity_event_score": liquidity_event_score,
            "continuation_score": continuation_score
        }
