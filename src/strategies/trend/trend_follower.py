from typing import List, Optional, Dict
from datetime import datetime
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.contracts.instrument_spec import InstrumentSpec
from src.core.contracts.strategy_params import TrendParams
from src.strategies.base import BaseStrategy
from src.features.technical_engine import TechnicalFeatureEngine
import numpy as np

class TrendFollower(BaseStrategy):
    """
    Deterministic Trend Following strategy that handles the full trend lifecycle.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("LifecycleTrendFollower", StrategyFamily.TREND, spec)
        self.lookback = 100

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [
            RegimeType.EARLY_TREND, 
            RegimeType.MID_TREND, 
            RegimeType.TREND_UP,
            RegimeType.TREND_DOWN,
            RegimeType.PULLBACK_IN_TREND
        ]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        params: TrendParams = self.get_params()
        if len(candles) < params.lookback_window: return False
        
        # Phase 6: Late-trend protection (instrument adjusted)
        exhaustion_limit = 0.8 + (1.0 - regime_state.instrument_adjustment) * 0.1
        if regime_state.exhaustion_risk > exhaustion_limit or regime_state.overextension > params.max_overextension:
            return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        regime = RegimeType(regime_state.regime_type)
        
        # HTF Alignment check
        if mtf_state:
            slope = features["sma_20_slope"][-1]
            direction = "long" if slope > 0 else "short"
            # If HTF is trending solidly against us, reject
            if direction == "long" and mtf_state.htf_state.direction == -1: return False
            if direction == "short" and mtf_state.htf_state.direction == 1: return False

        # Ignition Logic: Expansion from range
        if regime == RegimeType.EARLY_TREND:
            # Check for EMA stack start or breakout dist
            if abs(features["breakout_dist_upper"][-1]) < 0.5 or abs(features["breakout_dist_lower"][-1]) < 0.5:
                return True
        
        # Stable Trend Logic: Golden Cross or EMA slope
        if regime in [RegimeType.MID_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]:
             if abs(features["sma_20_slope"][-1]) > 0.001:
                  return True
                   
        return False

    def confirm_entry(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        # Require a candle close in direction of trend
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        slope = features["sma_20_slope"][-1]
        if slope > 0:
            return last.close > last.open
        else:
            return last.close < last.open

    def define_stop(self, candles: List[Candle]) -> float:
        params: TrendParams = self.get_params()
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        close = candles[-1].close
        slope = features["sma_20_slope"][-1]
        
        if slope > 0:
            return close - (atr * params.stop_multiplier)
        else:
            return close + (atr * params.stop_multiplier)

    def define_target(self, candles: List[Candle]) -> float:
        params: TrendParams = self.get_params()
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        close = candles[-1].close
        slope = features["sma_20_slope"][-1]
        
        if slope > 0:
            return close + (atr * params.target_multiplier)
        else:
            return close - (atr * params.target_multiplier)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        adx = features["adx"][-1]
        
        base_score = 0.4
        # ADX 25-50 is good, > 50 might be overextended
        if 25 < adx < 50: base_score = 0.8
        elif adx >= 50: base_score = 0.6
        
        # Phase 6: Health weighting
        base_score *= (regime_state.health_score + 0.3) 

        # Multi-timeframe confluence boost
        if mtf_state and mtf_state.confluence_score > 0.7:
            base_score = min(1.0, base_score + 0.1)
            
        return base_score

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Tighten stops if trend health deteriorates.
        """
        if len(candles) < 2: return None
        
        # Phase 6: Health-based Trailing
        if regime_state.health_score < 0.4:
             # Tighten significantly
             features = TechnicalFeatureEngine.get_candle_features(candles)
             atr = features["atr"][-1]
             close = candles[-1].close
             trade_dir = 1 if idea.direction == "long" else -1
             new_sl = close - (atr * 1.5 * trade_dir)
             return {"stop_loss": new_sl, "metadata": {"update_reason": "HEALTH_DETERIORATION"}}

        if regime_state.exhaustion_risk > 0.9:
             return {"exit": True, "metadata": {"update_reason": "EXHAUSTION_CRITICAL"}}

        return None

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        regime = RegimeType(regime_state.regime_type)
        if not self.is_valid_regime(regime): return None
        if not self.detect_setup(candles, regime_state, mtf_state): return None
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        slope = features["sma_20_slope"][-1]
        direction = "long" if slope > 0 else "short"
        
        entry = candles[-1].close
        sl = self.define_stop(candles)
        tp = self.define_target(candles)
        rr = abs(tp - entry) / (abs(entry - sl) + 1e-9)
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=regime,
            holding_period_hint="swing",
            timestamp=candles[-1].ts,
            metadata={
                "adx": features["adx"][-1], 
                "atr": features["atr"][-1],
                "mtf_bias": mtf_state.bias if mtf_state else "none"
            }
        )
