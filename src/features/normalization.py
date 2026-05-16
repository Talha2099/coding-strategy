import numpy as np
import pandas as pd
from typing import Dict, Optional, Any

class FeatureNormalizer:
    """
    STAGE H: Normalization and Instrument Awareness.
    Provides robust, causal scaling methods.
    """
    
    @staticmethod
    def rolling_zscore(series: np.ndarray, window: int = 200) -> np.ndarray:
        s = pd.Series(series)
        return ((s - s.rolling(window).mean()) / (s.rolling(window).std() + 1e-9)).values

    @staticmethod
    def robust_scale(series: np.ndarray, window: int = 200) -> np.ndarray:
        """Median / IQR Scaling (Robust to outliers)."""
        s = pd.Series(series)
        median = s.rolling(window).median()
        q75 = s.rolling(window).quantile(0.75)
        q25 = s.rolling(window).quantile(0.25)
        iqr = q75 - q25 + 1e-9
        return ((s - median) / iqr).values

    @staticmethod
    def percentile_rank(series: np.ndarray, window: int = 200) -> np.ndarray:
        """Rolling percentile rank [0, 1]."""
        def _get_rank(w):
            if len(w) < 2: return 0.5
            last = w[-1]
            return (w < last).sum() / (len(w) - 1)
        
        return pd.Series(series).rolling(window).apply(_get_rank, raw=True).values

    @staticmethod
    def instrument_adjust(feature_name: str, 
                          value: np.ndarray, 
                          archetype: float) -> np.ndarray:
        """
        Adjusts feature interpretation based on instrument archetype.
        archetype: 0 (Trend), 1 (Range), 2 (Volatile), 3 (Mean Reverting)
        """
        # Example: Scale breakout quality higher for Trend archetypes
        if "breakout" in feature_name and archetype == 0:
            return value * 1.2
        
        # Example: Dampen mean reversion score for high volatility archetypes
        if "mean_reversion" in feature_name and archetype == 2:
            return value * 0.8
            
        return value
