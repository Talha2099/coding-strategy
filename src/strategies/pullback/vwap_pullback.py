from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class VWAPPullback(BaseStrategy):
    """
    Buys dips to VWAP in uptrends, sells rallies in downtrends.
    Uses trend acceleration and rejection candles for confirmation.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("VWAPPullback", StrategyFamily.PULLBACK, spec)

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.TREND, RegimeType.PULLBACK_CONTINUATION, RegimeType.MID_TREND, RegimeType.PULLBACK_IN_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 50: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        vwap = features["vwap"]
        sma_50 = features["sma_50"]
        
        curr_price = closes[-1]
        curr_vwap = vwap[-1]
        
        # HTF Alignment
        if mtf_state:
            direction = "long" if curr_price > sma_50[-1] else "short"
            if direction == "long" and mtf_state.bias != "bullish": return False
            if direction == "short" and mtf_state.bias != "bearish": return False

        self.is_long = curr_price > sma_50[-1]
        self.is_short = curr_price < sma_50[-1]
        
        # Within strike distance of VWAP (0.15% for Gold/Indices/Stocks)
        dist_vwap = abs(curr_price - curr_vwap) / (curr_vwap + 1e-9)
        return dist_vwap < 0.0015

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Rejection candle (Hammer/Wick near VWAP)
        last_candle = candles[-1]
        stats = TechnicalFeatureEngine.get_candle_stats(
            np.array([last_candle.high]), 
            np.array([last_candle.low]), 
            np.array([last_candle.open]), 
            np.array([last_candle.close])
        )
        
        if self.is_long:
            # Look for lower wick rejection
            return stats["lower_wick_pct"][0] > 0.4
        else:
            # Look for upper wick rejection
            return stats["upper_wick_pct"][0] > 0.4

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        
        if self.is_long:
            return entry - (2.0 * atr)
        else:
            return entry + (2.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        
        if self.is_long:
            return entry + (4.0 * atr)
        else:
            return entry - (4.0 * atr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Higher score if slope of SMA 20 is strong in our direction
        slope = features["sma_20_slope"][-1]
        score = 0.5
        if self.is_long and slope > 0: score = 0.8
        elif self.is_short and slope < 0: score = 0.8
        
        # MTF confluence bonus
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        
        rr = abs(take_profit - entry_price) / (abs(stop_loss - entry_price) + 1e-9)
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction="long" if self.is_long else "short",
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            holding_period_hint="intraday",
            timestamp=candles[-1].ts
        )
