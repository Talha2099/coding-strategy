import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from src.core.types.strategy import RegimeType
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.types.trading import Candle, RegimeState

from src.regime.health import TrendHealthEngine
from src.regime.persistence import TrendPersistenceEngine

from src.core.contracts.instrument_spec import InstrumentSpec
from src.core.contracts.instrument_registry import InstrumentRegistry

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
        spec = InstrumentRegistry.get_spec(symbol)
        if len(candles) < 50:
            return self._default_state(symbol)

        features = TechnicalFeatureEngine.get_candle_features(candles)
        behavior = spec.behavior
        
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
        hurst = features.get("hurst", [0.5])[-1]
        
        # 1. Base Logic Flags (ADAPTED BY INSTRUMENT)
        # Some instruments are naturally more volatile: adjust 'high vol' threshold
        vol_mult = 2.0 * (1.0 + (behavior.volatility_regime_avg - 0.2))
        is_high_vol = curr_atr > hist_atr_mean * vol_mult
        
        # Trend threshold depends on persistence
        trend_threshold = 25.0 * (1.0 - (behavior.trend_persistence - 0.5) * 0.4)
        is_trending_adx = curr_adx > trend_threshold
        
        rel_vol = features["rel_vol"][-1]
        breakout_dist_upper = features["breakout_dist_upper"][-1]
        breakout_dist_lower = features["breakout_dist_lower"][-1]
        
        # 2. Detect Regimes & Lifecycle Stages
        probabilities = {r.value: 0.0 for r in RegimeType}
        regime = RegimeType.RANGE # Default
        stage = 0 
        
        # Determine core direction
        is_up = sma_20_slope > 0
        direction = 1 if is_up else -1 if sma_20_slope < 0 else 0
        
        # Live Health Monitoring (needed for classification)
        health_metrics = self.health_engine.evaluate_health(candles, "trend", direction)
        health = health_metrics["health_score"]
        exhaustion = health_metrics["exhaustion_risk"]
        overextension = health_metrics["overextension"]
        persistence = health_metrics["persistence"]
        
        # TRANSITION LOGIC & REGIME DETECTION
        
        # A. VOLATILE UNSTABLE / EXTREME GAP
        if is_high_vol and curr_adx < 20:
             regime = RegimeType.VOLATILE_UNSTABLE
             stage = 0
        elif abs(features["gap_size"][-1]) > (0.01 * behavior.news_sensitivity):
             regime = RegimeType.GAP_DRIVEN
             stage = 0

        # B. TREND LIFECYCLE (Priority Detection)
        elif is_trending_adx or health > 0.4:
            if exhaustion > 0.8:
                regime = RegimeType.EXHAUSTION_RISK
                stage = 6
            elif health_metrics["acceleration"] < -0.0001 and curr_adx > 40:
                regime = RegimeType.REVERSAL_RISK
                stage = 7
            elif health_metrics["is_continuation"] > 0 and persistence > 0.7:
                regime = RegimeType.MID_TREND if health > 0.7 else RegimeType.CONFIRMED_TREND
                stage = 3
            elif curr_adx < 25 and health > 0.5:
                regime = RegimeType.EARLY_TREND
                stage = 1
            elif (is_up and curr_price < features["ema_20"][-1]) or (not is_up and curr_price > features["ema_20"][-1]):
                if health > 0.6: 
                    regime = RegimeType.CONTINUATION_READY
                    stage = 4
                else:
                    regime = RegimeType.PULLBACK_IN_TREND
                    stage = 4
            elif overextension > 2.5:
                regime = RegimeType.LATE_TREND
                stage = 5
            else:
                regime = RegimeType.TREND_UP if is_up else RegimeType.TREND_DOWN
                stage = 2

        # C. BREAKOUT LIFECYCLE
        elif (breakout_dist_upper > 0 or breakout_dist_lower < 0) and rel_vol > 1.2:
            if rel_vol > 2.0 or abs(features["returns"][-1]) > curr_atr / curr_price:
                regime = RegimeType.BREAKOUT_ACTIVE
                stage = 1
            else:
                regime = RegimeType.POST_BREAKOUT_CONTINUATION
                stage = 2

        # D. PRE_TREND / COMPRESSION
        elif bb_squeeze > 0.5 or bb_width < np.percentile(features["bb_width"][-100:], 25):
            regime = RegimeType.PRE_TREND_COMPRESSION
            stage = 0
        
        # E. RANGE & MEAN REVERSION LIFECYCLE
        else:
            # Adjust range definition by mean reversion propensity
            range_hurst_cutoff = 0.55 + (behavior.mean_reversion_propensity - 0.5) * 0.2
            is_range_context = curr_adx < trend_threshold and hurst < range_hurst_cutoff
            zscore = features["zscore"][-1]
            
            # Boundary Proximity
            at_high = breakout_dist_upper < 0.15 and breakout_dist_upper > -0.05
            at_low = breakout_dist_lower > -0.15 and breakout_dist_lower < 0.05
            
            if is_range_context:
                mr_threshold = 2.2 - (behavior.mean_reversion_propensity - 0.5) * 0.5
                if (curr_rsi > 70 or curr_rsi < 30 or abs(zscore) > mr_threshold):
                    regime = RegimeType.MEAN_REVERSION_SETUP
                    stage = 1
                elif at_high:
                    regime = RegimeType.RANGE_HIGH_TOUCH
                    stage = 2
                elif at_low:
                    regime = RegimeType.RANGE_LOW_TOUCH
                    stage = 2
                elif hurst < 0.4 and bb_width < np.mean(features["bb_width"][-50:]):
                    regime = RegimeType.RANGE_ESTABLISHED
                    stage = 1
                elif bb_squeeze > 0.4:
                    regime = RegimeType.PRE_TREND_COMPRESSION
                    stage = 0
                else:
                    regime = RegimeType.RANGE_FORMING
                    stage = 0
            elif abs(zscore) > 2.5 and hurst < 0.45:
                regime = RegimeType.MEAN_REVERTING
                stage = 2
            else:
                regime = RegimeType.RANGE
                stage = 0
        
        probabilities[regime.value] = 1.0 # Simplified for now

        self.last_regime = regime
        self.regime_history.append(regime)
        if len(self.regime_history) > 100: self.regime_history.pop(0)
        
        # Phase 9: Persistence Analysis
        hurst = health_metrics["hurst"]
        
        return RegimeState(
            symbol=symbol,
            regime_type=regime.value,
            lifecycle_stage=stage,
            probabilities=probabilities,
            volatility=curr_vol,
            trend_strength=curr_adx,
            direction=direction,
            health_score=health,
            hurst=hurst,
            persistence=persistence,
            candle_quality=health_metrics["candle_quality"],
            acceleration=health_metrics["acceleration"],
            overextension=overextension,
            exhaustion_risk=exhaustion,
            instrument_adjustment=behavior.trend_persistence, # New field
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
