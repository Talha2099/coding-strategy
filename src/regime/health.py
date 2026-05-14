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
                "exhaustion_risk": 0.0,
                "persistence": 0.5,
                "hurst": 0.5,
                "candle_quality": 0.5,
                "follow_through": 0.5
            }
            
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        highs = features["high"]
        lows = features["low"]
        
        # 1. Slope and Acceleration
        y = closes[-20:]
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        
        y_prev = closes[-40:-20]
        slope_prev, _ = np.polyfit(x, y_prev, 1)
        acceleration = slope - slope_prev
        norm_slope = slope / (closes[-1] + 1e-9)
        
        # 2. Overextension (Distance from Mean)
        sma_50 = features["sma_50"][-1]
        dist_from_mean = (closes[-1] - sma_50) / (sma_50 + 1e-9)
        overextension = abs(dist_from_mean) * 10.0
        
        # 3. Pullback Behavior (Stability)
        last_10 = candles[-10:]
        if direction == 1:
            pullbacks = [c.low for c in last_10 if c.close < c.open]
            retracement_depth = (max(highs[-10:]) - min(pullbacks)) / (max(highs[-10:]) - min(lows[-10:]) + 1e-9) if pullbacks else 0
        else:
            pullbacks = [c.high for c in last_10 if c.close > c.open]
            retracement_depth = (max(pullbacks) - min(lows[-10:])) / (max(highs[-10:]) - min(lows[-10:]) + 1e-9) if pullbacks else 0
            
        # 4. Persistence & Hurst Approximation
        returns = np.diff(closes[-50:])
        persistence = np.mean(np.sign(returns) == direction) if direction != 0 else 0.5
        
        # Simple Hurst: R/S approximation
        res = returns - np.mean(returns)
        cum_res = np.cumsum(res)
        r = np.max(cum_res) - np.min(cum_res)
        s = np.std(returns) + 1e-9
        hurst = min(1.0, max(0.0, 0.5 * (np.log(r/s) / np.log(len(returns)))))
        
        # 5. Candle Quality & Follow-through
        # Ratio of bodies to total range in trend direction
        body_sizes = [abs(c.close - c.open) for c in last_10]
        ranges = [c.high - c.low + 1e-9 for c in last_10]
        candle_quality = np.mean([b/r for b, r in zip(body_sizes, ranges)])
        
        # Follow-through: probability that N+1 candle is in same direction as N
        dirs = np.sign(returns)
        matches = [1 if dirs[i] == dirs[i-1] else 0 for i in range(1, len(dirs))]
        follow_through = np.mean(matches) if matches else 0.5
        
        # 6. Structure Continuation (HH/LL)
        if direction == 1:
            is_continuation = highs[-1] > max(highs[-10:-1]) and lows[-1] > min(lows[-10:-1])
        elif direction == -1:
            is_continuation = lows[-1] < min(lows[-10:-1]) and highs[-1] < max(highs[-10:-1])
        else:
            is_continuation = False
        
        # 7. Volatility Expansion
        atr = features["atr"]
        atr_sma = np.mean(atr[-20:])
        vol_ratio = atr[-1] / (atr_sma + 1e-9)
        
        # 8. Exhaustion Signals
        rsi = features["rsi"][-1]
        rsi_exhaustion = 0.0
        if direction == 1 and rsi > 80: rsi_exhaustion = (rsi - 80) / 20.0
        if direction == -1 and rsi < 20: rsi_exhaustion = (20 - rsi) / 20.0
        
        vols = [c.volume for c in last_10]
        vol_spike = vols[-1] / (np.mean(vols) + 1e-9)
        exhaustion_risk = min(1.0, (rsi_exhaustion * 0.4) + (vol_spike * 0.2) + (overextension * 0.4))
        
        # 9. Final Trend Health Score
        slope_quality = min(1.0, abs(norm_slope) * 500)
        vol_stability = max(0.0, 1.0 - abs(vol_ratio - 1.0) * 0.5)
        
        health_score = (
            slope_quality * 0.3 +
            persistence * 0.2 +
            candle_quality * 0.1 +
            (1.0 if is_continuation else 0.5) * 0.2 +
            (1.0 - exhaustion_risk) * 0.2
        )
        
        return {
            "health_score": float(health_score),
            "acceleration": float(acceleration),
            "overextension": float(overextension),
            "exhaustion_risk": float(exhaustion_risk),
            "persistence": float(persistence),
            "hurst": float(hurst),
            "candle_quality": float(candle_quality),
            "follow_through": float(follow_through),
            "is_continuation": float(1.0 if is_continuation else 0.0)
        }

    def get_late_trend_protection(self, health: Dict[str, float]) -> bool:
        """
        Returns True if fresh entries should be blocked due to trend maturity/exhaustion.
        """
        if health["exhaustion_risk"] > 0.8: return True
        if health["overextension"] > 3.0: return True
        if health["health_score"] < 0.3: return True
        return False
