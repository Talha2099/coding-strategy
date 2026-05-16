import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.types.trading import Candle

class LifecycleFeatureEngine:
    """
    STAGE E: Lifecycle Features.
    Tracks move stability, pullbacks, and exhaustion risk.
    """
    
    @staticmethod
    def extract(raw_features: Dict[str, np.ndarray], context_features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        if not raw_features: return {}
        
        closes = raw_features["close"]
        highs = raw_features["high"]
        lows = raw_features["low"]
        atr = raw_features["atr"]
        
        # 1. Pullback Depth
        max_high = pd.Series(highs).rolling(20).max()
        min_low = pd.Series(lows).rolling(20).min()
        
        pullback_depth_bull = (max_high - closes) / (atr + 1e-9)
        pullback_depth_bear = (closes - min_low) / (atr + 1e-9)
        
        # 2. Exhaustion Score (Extreme distance from value)
        ema_20 = pd.Series(closes).ewm(span=20, adjust=False).mean().values
        dist_ema20 = (closes - ema_20) / (atr + 1e-9)
        
        rel_vol = context_features.get("rel_vol", np.ones_like(closes))
        rsi = raw_features.get("rsi", np.full_like(closes, 50))
        
        exhaustion_score = np.where(
            (np.abs(dist_ema20) > 4.0) & 
            (rel_vol > 2.0) & 
            ((rsi > 80) | (rsi < 20)), 
            1.0, 0.0
        )
        
        # 3. Efficiency Ratio (Fractal Efficiency)
        net_dist = np.abs(closes - pd.Series(closes).shift(20).values)
        path_len = pd.Series(np.abs(np.diff(closes, prepend=closes[0]))).rolling(20).sum().values
        efficiency = net_dist / (path_len + 1e-9)
        
        # 4. Trend Lifecycle (Numeric state 0-7)
        # 0: Flat/Unknown, 1: Ignition, 2: Expansion, 3: Mature, 4: Exhaustion, 5: Pullback
        ema_cross = raw_features.get("ema_cross", np.zeros_like(closes))
        adx = raw_features.get("adx", np.zeros_like(closes))
        trend_lifecycle = np.zeros_like(closes)
        
        trend_lifecycle = np.where((ema_cross != 0) & (adx < 25), 1.0, trend_lifecycle) # Ignition
        trend_lifecycle = np.where((adx >= 25) & (adx < 45), 2.0, trend_lifecycle) # Expansion
        trend_lifecycle = np.where((adx >= 45), 3.0, trend_lifecycle) # Mature
        trend_lifecycle = np.where(exhaustion_score > 0.5, 4.0, trend_lifecycle) # Exhaustion
        trend_lifecycle = np.where((pullback_depth_bull > 1.5) | (pullback_depth_bear > 1.5), 5.0, trend_lifecycle) # Pullback
        
        # 5. Breakout Lifecycle
        bb_squeeze = raw_features.get("bb_squeeze", np.zeros_like(closes))
        displacement = raw_features.get("displacement", np.zeros_like(closes))
        breakout_lifecycle = np.zeros_like(closes)
        
        breakout_lifecycle = np.where(bb_squeeze > 0.5, 1.0, breakout_lifecycle) # Compression
        breakout_lifecycle = np.where((bb_squeeze < 0.5) & (displacement > 0.5), 2.0, breakout_lifecycle) # Ignition
        
        return {
            "pullback_depth_bull": pullback_depth_bull.values,
            "pullback_depth_bear": pullback_depth_bear.values,
            "exhaustion_score": exhaustion_score,
            "efficiency": efficiency,
            "trend_lifecycle": trend_lifecycle,
            "breakout_lifecycle": breakout_lifecycle
        }
