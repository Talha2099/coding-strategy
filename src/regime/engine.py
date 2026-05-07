import numpy as np
from typing import Dict, List, Optional
from src.core.types.strategy import RegimeType
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.types.trading import Candle

class RegimeEngine:
    """
    Classifies market state using technical indicators.
    Decides which strategy families should be active.
    """
    def __init__(self, window: int = 50):
        self.window = window

    def classify(self, candles: List[Candle]) -> RegimeType:
        if len(candles) < self.window:
            return RegimeType.VOLATILE_UNSTABLE

        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        sma_20 = features["sma_20"]
        sma_50 = features["sma_50"]
        atr = features["atr"]
        rsi = features["rsi"]
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        
        curr_price = closes[-1]
        prev_price = closes[-2]
        
        # 1. Trend Detection
        is_trending_bull = curr_price > sma_20[-1] > sma_50[-1]
        is_trending_bear = curr_price < sma_20[-1] < sma_50[-1]
        
        # Slope of SMA 20
        sma_slope = (sma_20[-1] - sma_20[-5]) / 5 if len(sma_20) > 5 else 0
        
        # 2. Breakout Detection
        volatility_expansion = atr[-1] > np.mean(atr[-10:]) * 1.5 if len(atr) > 10 else False
        price_at_high = curr_price >= np.max(closes[-self.window:-1])
        price_at_low = curr_price <= np.min(closes[-self.window:-1])
        
        if volatility_expansion and (price_at_high or price_at_low):
            return RegimeType.BREAKOUT
            
        # 3. Pullback Detection
        if is_trending_bull and prev_price > curr_price and curr_price <= sma_20[-1] * 1.01:
            return RegimeType.PULLBACK
        if is_trending_bear and prev_price < curr_price and curr_price >= sma_20[-1] * 0.99:
            return RegimeType.PULLBACK
            
        # 4. Ranging vs Mean Reversion
        adx_approx = abs(rsi[-1] - 50) # Very rough ADX proxy using RSI divergence from 50
        bb_width = (bb_upper[-1] - bb_lower[-1]) / sma_20[-1]
        
        if bb_width < 0.02: # Compressed range
            return RegimeType.RANGING
            
        if adx_approx < 10:
            return RegimeType.MEAN_REVERSION

        # 5. Volatility Shock
        if atr[-1] > np.mean(atr[-20:]) * 3:
            return RegimeType.VOLATILE_UNSTABLE

        if is_trending_bull: return RegimeType.TRENDING_BULL
        if is_trending_bear: return RegimeType.TRENDING_BEAR
        
        return RegimeType.MEAN_REVERSION # Default to MR if no strong trend
