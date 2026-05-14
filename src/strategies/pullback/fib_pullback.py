from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class FibPullback(BaseStrategy):
    """
    Trades pullbacks to Fibonacci retracement levels (0.5, 0.618) in strong trends.
    """
    def __init__(self, spec: InstrumentSpec, lookback: int = 50):
        super().__init__("FibPullback", StrategyFamily.PULLBACK, spec)
        self.lookback = lookback

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.TREND, RegimeType.PULLBACK_CONTINUATION, RegimeType.MID_TREND, RegimeType.PULLBACK_IN_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.lookback: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        highs = features["high"]
        lows = features["low"]
        closes = features["close"]
        sma_50 = features["sma_50"]
        
        # Determine trend
        direction = "long" if closes[-1] > sma_50[-1] else "short"
        
        # HTF Alignment
        if mtf_state:
            if direction == "long" and mtf_state.bias != "bullish": return False
            if direction == "short" and mtf_state.bias != "bearish": return False

        self.is_long = direction == "long"
        self.is_short = direction == "short"
        
        # Find the recent swing high/low in this lookback
        swing_high = np.max(highs[-self.lookback:])
        swing_low = np.min(lows[-self.lookback:])
        swing_range = swing_high - swing_low
        
        if swing_range == 0: return False
        
        self.fib_618 = 0.0
        self.fib_50 = 0.0
        
        if self.is_long:
            # Bullish trend: pullback to Fib levels
            self.fib_618 = swing_high - (swing_range * 0.618)
            self.fib_50 = swing_high - (swing_range * 0.5)
            # Check if current LOW is near these levels
            curr_low = candles[-1].low
            return curr_low <= self.fib_50 and curr_low >= self.fib_618 * 0.995
        else:
            # Bearish trend
            self.fib_618 = swing_low + (swing_range * 0.618)
            self.fib_50 = swing_low + (swing_range * 0.5)
            curr_high = candles[-1].high
            return curr_high >= self.fib_50 and curr_high <= self.fib_618 * 1.005

    def confirm_entry(self, candles: List[Candle]) -> bool:
        last = candles[-1]
        # Reversal candle off the fib zone
        if self.is_long:
            return last.close > last.open
        else:
            return last.close < last.open

    def define_stop(self, candles: List[Candle]) -> float:
        # Stop below the 78.6% retracement or recent swing
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        return entry - (1.5 * atr) if self.is_long else entry + (1.5 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        # Target the swing high/low
        features = TechnicalFeatureEngine.get_candle_features(candles)
        highs = features["high"]
        lows = features["low"]
        if self.is_long:
            return np.max(highs[-self.lookback:])
        else:
            return np.min(lows[-self.lookback:])

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.75
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = 0.85
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        if rr < 1.3: return None
 
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
            holding_period_hint="swing",
            timestamp=candles[-1].ts
        )
