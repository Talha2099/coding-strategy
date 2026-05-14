import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from src.core.types.strategy import RegimeType
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.types.trading import Candle, RegimeState

from src.regime.health import TrendHealthEngine
from src.regime.persistence import TrendPersistenceEngine

class RegimeEngine:
    """
    Advanced market state classifier that detects regimes and transitions.
    Uses technical features and structural context to solve lag issues.
    """
    def __init__(self, window: int = 200):
        self.window = window
        self.last_regime: Optional[RegimeType] = None
        self.regime_history: List[RegimeType] = []
        self.health_engine = TrendHealthEngine()

    def classify(self, candles: List[Candle], symbol: str) -> RegimeState:
        if len(candles) < 50:
            return self._default_state(symbol)

        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # Current values
        curr_price = features["close"][-1]
        curr_atr = features["atr"][-1]
        hist_atr_mean = np.mean(features["atr"][-20:])
        curr_rsi = features["rsi"][-1]
        curr_adx = features["adx"][-1]
        curr_vol = features["realized_vol"][-1]
        bb_width = features["bb_width"][-1]
        bb_squeeze = features["bb_squeeze"][-1]
        sma_20_slope = features["sma_20_slope"][-1]
        sma_20_curve = features["sma_20_curve"][-1]
        exhaustion_score = features["exhaustion_score"][-1]
        
        # 1. Base Logic Flags
        is_high_vol = curr_atr > hist_atr_mean * 2.0
        is_trending_adx = curr_adx > 25
        is_strong_trend_adx = curr_adx > 45
        is_bull_stack = features["ema_20"][-1] > features["ema_50"][-1] > features["ema_200"][-1]
        is_bear_stack = features["ema_20"][-1] < features["ema_50"][-1] < features["ema_200"][-1]
        
        rel_vol = features["rel_vol"][-1]
        breakout_dist_upper = features["breakout_dist_upper"][-1]
        breakout_dist_lower = features["breakout_dist_lower"][-1]
        
        # 2. Detect Regimes & Lifecycle Stages
        probabilities = {r.value: 0.0 for r in RegimeType}
        regime = RegimeType.RANGE # Default
        stage = 0 # Default to pre-trend
        
        # Determine core direction
        is_up = sma_20_slope > 0
        
        # TRANSITION LOGIC & REGIME DETECTION
        
        # A. VOLATILE UNSTABLE / EXTREME GAP
        if is_high_vol and curr_adx < 20:
             regime = RegimeType.VOLATILE_UNSTABLE
             stage = 0
             probabilities[regime.value] = 0.9
        elif abs(features["gap_size"][-1]) > 0.01:
             regime = RegimeType.GAP_DRIVEN
             stage = 0
             probabilities[regime.value] = 0.8

        # B. BREAKOUT LIFECYCLE (Priority Detection)
        elif (breakout_dist_upper > 0 or breakout_dist_lower < 0) and rel_vol > 1.2:
            # Active breakout or immediate post-breakout
            if rel_vol > 2.0 or abs(features["returns"][-1]) > curr_atr / curr_price:
                regime = RegimeType.BREAKOUT_ACTIVE
                stage = 1
            else:
                regime = RegimeType.POST_BREAKOUT_CONTINUATION
                stage = 2
            probabilities[regime.value] = 0.8
            
            # Detect False Breakout Risk (Lagging price, fading volume)
            if rel_vol < 1.0 and abs(features["returns"][-1]) < 1e-4:
                regime = RegimeType.FALSE_BREAKOUT_RISK
                probabilities[regime.value] = 0.6

        # C. TREND LIFECYCLE
        elif is_bull_stack or is_bear_stack or is_trending_adx:
            regime = RegimeType.TREND_UP if is_up else RegimeType.TREND_DOWN
            
            if exhaustion_score > 0.5 or (is_strong_trend_adx and sma_20_curve < 0):
                regime = RegimeType.TREND_EXHAUSTION
                stage = 5
            elif (is_bull_stack and is_up) or (is_bear_stack and not is_up):
                dist_ema20 = (curr_price - features["ema_20"][-1]) / (curr_atr + 1e-9)
                if (is_up and -1.0 < dist_ema20 < 0.2) or (not is_up and -0.2 < dist_ema20 < 1.0):
                    regime = RegimeType.PULLBACK_IN_TREND
                    stage = 4
                else:
                    regime = RegimeType.MID_TREND
                    stage = 3 # Healthy continuation
            elif is_trending_adx:
                regime = RegimeType.EARLY_TREND
                stage = 2 # Confirmed start

            # Final check for Reversal Risk in Trend
            if sma_20_curve < -2.0 and curr_adx > 30: # Sharp deceleration
                regime = RegimeType.REVERSAL_RISK
                probabilities[regime.value] = 0.7

        # D. PRE-BREAKOUT / COMPRESSION
        elif bb_squeeze > 0.5 or bb_width < np.percentile(features["bb_width"][-100:], 25):
            regime = RegimeType.BREAKOUT_PREP
            stage = 0
            probabilities[regime.value] = 0.8
        
        # E. MEAN REVERTING / RANGE
        else:
            if curr_rsi > 70 or curr_rsi < 30 or abs(features["zscore"][-1]) > 2.0:
                regime = RegimeType.MEAN_REVERTING
                probabilities[regime.value] = 0.7
            else:
                regime = RegimeType.RANGE
                probabilities[regime.value] = 0.6

        self.last_regime = regime
        self.regime_history.append(regime)
        if len(self.regime_history) > 100: self.regime_history.pop(0)
        
        # Phase 6: Live Health Monitoring
        direction = 1 if is_up else -1 if sma_20_slope < 0 else 0
        health_metrics = self.health_engine.evaluate_health(candles, regime.value, direction)
        
        # Phase 9: Persistence Analysis
        hurst = TrendPersistenceEngine.compute_hurst([c.close for c in candles[-100:]])
        
        return RegimeState(
            symbol=symbol,
            regime_type=regime.value,
            lifecycle_stage=stage,
            probabilities=probabilities,
            volatility=curr_vol,
            trend_strength=curr_adx,
            direction=direction,
            health_score=health_metrics["health_score"],
            hurst=hurst,
            acceleration=health_metrics["acceleration"],
            overextension=health_metrics["overextension"],
            exhaustion_risk=health_metrics["exhaustion_risk"],
            timestamp=candles[-1].ts
        )

    def _default_state(self, symbol: str) -> RegimeState:
        return RegimeState(
            symbol=symbol,
            regime_type=RegimeType.RANGE.value,
            lifecycle_stage=0,
            probabilities={r.value: 0.1 for r in RegimeType},
            volatility=0.0,
            trend_strength=0.0,
            direction=0,
            timestamp=datetime.utcnow()
        )
