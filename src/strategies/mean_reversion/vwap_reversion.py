from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class VWAPReversion(BaseStrategy):
    """
    Mean reversion strategy targeting VWAP when price is overextended.
    """
    def __init__(self, spec: InstrumentSpec, dev_threshold: float = 2.5):
        super().__init__("VWAPReversion", StrategyFamily.MEAN_REVERSION, spec)
        self.dev_threshold = dev_threshold

    def is_valid_regime(self, regime: RegimeType) -> bool:
        # Only active in non-trending or late-trend regimes
        return regime in [RegimeType.RANGE, RegimeType.MEAN_REVERTING, RegimeType.LATE_TREND, RegimeType.VOLATILE_UNSTABLE]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 50: return False
        
        # HTF Trend check - disable if HTF is trending strongly
        if mtf_state and mtf_state.confluence_score > 0.8:
            return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        curr_price = candles[-1].close
        curr_vwap = features["vwap"][-1]
        curr_std = np.std([c.close for c in candles[-50:]])
        
        # Calculate price distance from VWAP in units of standard deviation
        z_score_vwap = (curr_price - curr_vwap) / (curr_std + 1e-9)
        
        self.is_long = z_score_vwap < -self.dev_threshold
        self.is_short = z_score_vwap > self.dev_threshold
        
        # Down-weight if in mid-trend (should be blocked by is_valid_regime, but added for safety)
        if regime_state.lifecycle_stage in [1, 2, 3]:
             return False
             
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Wait for a reversal candle close
        last = candles[-1]
        if self.is_long: return last.close > last.open
        if self.is_short: return last.close < last.open
        return False

    def define_stop(self, candles: List[Candle]) -> float:
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        return last.close - (atr * 2) if self.is_long else last.close + (atr * 2)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        return features["vwap"][-1]

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        # Better score if regime is specifically RANGING
        regime = RegimeType(regime_state.regime_type)
        score = 0.5
        if regime == RegimeType.RANGE: score = 0.8
        elif regime == RegimeType.LATE_TREND: score = 0.6 # Catching the dead cat bounce or exhaustion
        
        if mtf_state and mtf_state.bias == "neutral":
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry = candles[-1].close
        sl = self.define_stop(candles)
        tp = self.define_target(candles)
        rr = abs(tp - entry) / (abs(entry - sl) + 1e-9)
        
        if rr < 1.0: return None
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction="long" if self.is_long else "short",
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
