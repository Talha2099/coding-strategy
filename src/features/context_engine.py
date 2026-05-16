import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.types.trading import Candle

from src.core.contracts.instrument_registry import InstrumentRegistry

class ContextFeatureEngine:
    """
    STAGE B: Market Context Enrichment.
    Calculates session-aware, volatility-aware, and relative performance features.
    """
    
    @staticmethod
    def get_session_labels(timestamps: List[any], symbol: Optional[str] = None) -> np.ndarray:
        def _get_val(ts):
            if symbol:
                return InstrumentRegistry.get_session(pd.to_datetime(ts), symbol).value
            h = pd.to_datetime(ts).hour
            if 0 <= h < 7: return 1 # ASIA
            if 7 <= h < 12: return 2 # LONDON
            if 12 <= h < 16: return 3 # NY
            if 16 <= h < 21: return 4 # NY_CLOSE
            return 0 
        return np.array([_get_val(ts) for ts in timestamps])

    @staticmethod
    def extract(raw_features: Dict[str, np.ndarray], candles: List[Candle], symbol: Optional[str] = None) -> Dict[str, np.ndarray]:
        if not raw_features: return {}
        
        closes = raw_features["close"]
        highs = raw_features["high"]
        lows = raw_features["low"]
        volumes = raw_features["volume"]
        log_returns = raw_features["log_returns"]
        atr = raw_features.get("atr", np.zeros_like(closes))
        
        # 1. Relative Volume
        vol_sma = pd.Series(volumes).rolling(window=20).mean().values
        rel_vol = volumes / (vol_sma + 1e-9)
        
        # 2. Volatility Context
        realized_vol = pd.Series(log_returns).rolling(window=14).std().values * np.sqrt(252 * 1440)
        vol_ma = pd.Series(realized_vol).rolling(50).mean().values
        vol_regime = np.where(realized_vol > vol_ma * 1.5, 2.0, np.where(realized_vol < vol_ma * 0.7, 0.0, 1.0))
        
        # 3. Session Context
        timestamps = [c.ts for c in candles]
        session_labels = ContextFeatureEngine.get_session_labels(timestamps, symbol)
        
        # 4. Z-Score (Statistical Stretch)
        sma_20 = pd.Series(closes).rolling(20).mean().values
        std_20 = pd.Series(closes).rolling(20).std().values
        zscore = (closes - sma_20) / (std_20 + 1e-9)

        # 5. Liquidity / Level Context
        # Distance to prior session high/low
        # We find where session label changes
        session_change = np.where(pd.Series(session_labels).diff() != 0, 1, 0)
        
        # For simplicity in vectorized form, let's use a rolling daily max/min as proxy for session levels
        # A more precise one would group by session label and shift(1)
        # But rolling(window=240) handles M5-M15 roughly
        prior_high = pd.Series(highs).shift(1).rolling(150, min_periods=1).max().values
        prior_low = pd.Series(lows).shift(1).rolling(150, min_periods=1).min().values
        
        dist_to_prior_high = (highs - prior_high) / (atr + 1e-9)
        dist_to_prior_low = (lows - prior_low) / (atr + 1e-9)
        
        context = {
            "rel_vol": rel_vol,
            "realized_vol": realized_vol,
            "vol_regime": vol_regime,
            "session_labels": session_labels.astype(float),
            "zscore": zscore,
            "dist_to_session_high": dist_to_prior_high,
            "dist_to_session_low": dist_to_prior_low
        }

        # 6. Instrument Context
        if symbol:
            spec = InstrumentRegistry.get_spec(symbol)
            length = len(closes)
            context.update({
                "instrument_archetype": np.full(length, spec.behavior.archetype.value, dtype=float),
                "asset_class": np.full(length, spec.asset_class.value, dtype=float),
                "point_value": np.full(length, float(spec.point_value)),
                "tick_size": np.full(length, float(spec.tick_size)),
                "news_sensitivity": np.full(length, float(spec.behavior.news_sensitivity))
            })
        
        return context
