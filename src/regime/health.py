from typing import List, Dict, Any
import numpy as np
from datetime import datetime
from src.core.types.trading import Candle, RegimeState
from src.features.technical_engine import TechnicalFeatureEngine

class TrendHealthEngine:
    """
    PHASE 6: Continuous trend monitoring and health scoring.
    Evaluates trend sustainability, maturity, and risk of reversal.
    """
    
    def __init__(self, window: int = 50):
        self.window = window

    def evaluate_health(self, candles: List[Candle], current_type: str, direction: int) -> Dict[str, float]:
        if len(candles) < self.window:
            return {
                "health_score": 0.5,
                "acceleration": 0.0,
                "overextension": 0.0,
                "exhaustion_risk": 0.0
            }
            
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        highs = features["high"]
        lows = features["low"]
        
        # 1. Slope and Acceleration
        # Linear regression on last 20 closes to get slope
        y = closes[-20:]
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        
        # Acceleration: rate of change of slope
        y_prev = closes[-40:-20]
        slope_prev, _ = np.polyfit(x, y_prev, 1)
        acceleration = slope - slope_prev
        
        # Normalize slope by price level
        norm_slope = slope / (closes[-1] + 1e-9)
        
        # 2. Overextension (Distance from Mean)
        sma_50 = features["sma_50"][-1]
        dist_from_mean = (closes[-1] - sma_50) / (sma_50 + 1e-9)
        overextension = abs(dist_from_mean) * 10.0 # Scale it
        
        # 3. Pullback Behavior (Stability)
        # Ratio of body size to wick size in trend direction
        last_10 = candles[-10:]
        if direction == 1:
            pullbacks = [c.low for c in last_10 if c.close < c.open]
            retracement_depth = (max(highs[-10:]) - min(pullbacks)) / (max(highs[-10:]) - min(lows[-10:]) + 1e-9) if pullbacks else 0
        else:
            pullbacks = [c.high for c in last_10 if c.close > c.open]
            retracement_depth = (max(pullbacks) - min(lows[-10:])) / (max(highs[-10:]) - min(lows[-10:]) + 1e-9) if pullbacks else 0
            
        # 4. Volatility Expansion
        atr = features["atr"]
        atr_sma = np.mean(atr[-20:])
        vol_ratio = atr[-1] / (atr_sma + 1e-9)
        
        # 5. Exhaustion Signals
        # - Extreme RSI
        rsi = features["rsi"][-1]
        rsi_exhaustion = 0.0
        if direction == 1 and rsi > 80: rsi_exhaustion = (rsi - 80) / 20.0
        if direction == -1 and rsi < 20: rsi_exhaustion = (20 - rsi) / 20.0
        
        # - Volume Climax (approximation)
        vols = [c.volume for c in last_10]
        vol_spike = vols[-1] / (np.mean(vols) + 1e-9)
        
        exhaustion_risk = min(1.0, (rsi_exhaustion * 0.5) + (vol_spike * 0.3) + (overextension * 0.2))
        
        # 6. Trend Health Score Calculation
        # Components: Slope Strength, Low Volatility (stability), Normal Retracements, Low Exhaustion
        slope_quality = min(1.0, abs(norm_slope) * 500)
        vol_stability = max(0.0, 1.0 - abs(vol_ratio - 1.0))
        retracement_quality = max(0.0, 1.0 - abs(retracement_depth - 0.38)) # 38% is "healthy"
        
        health_score = (
            slope_quality * 0.4 +
            vol_stability * 0.2 +
            retracement_quality * 0.2 +
            (1.0 - exhaustion_risk) * 0.2
        )
        
        return {
            "health_score": float(health_score),
            "acceleration": float(acceleration),
            "overextension": float(overextension),
            "exhaustion_risk": float(exhaustion_risk)
        }

    def get_late_trend_protection(self, health: Dict[str, float]) -> bool:
        """
        Returns True if fresh entries should be blocked due to trend maturity/exhaustion.
        """
        if health["exhaustion_risk"] > 0.8: return True
        if health["overextension"] > 3.0: return True
        if health["health_score"] < 0.3: return True
        return False
