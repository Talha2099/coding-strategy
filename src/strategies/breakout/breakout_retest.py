from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class BreakoutRetest(BaseStrategy):
    """
    Waits for a breakout of a major level and then trades the first retest of that level.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 20):
        super().__init__("BreakoutRetest", StrategyFamily.BREAKOUT, spec)
        self.window = window

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.BREAKOUT, RegimeType.TREND, RegimeType.PULLBACK_CONTINUATION, RegimeType.EARLY_TREND, RegimeType.MID_TREND]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.window + 20: return False
        
        # HTF Alignment
        if mtf_state:
             # Basic trend detection for retest
             if mtf_state.bias == "neutral": return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        highs = features["high"]
        lows = features["low"]
        
        # Identify the previous major level that was broken
        # Look back for a 'recent' breakout (last 10-15 bars)
        
        self.is_long = False
        self.is_short = False
        self.breakout_level = 0.0
        
        # Bullish Retest
        recent_highs = highs[-(self.window+20):-1]
        for i in range(len(recent_highs) - self.window - 1, len(recent_highs) - 5):
            ref_high = np.max(highs[i-self.window:i])
            if highs[i] > ref_high:
                self.breakout_level = ref_high
                if closes[-1] > self.breakout_level and lows[-1] <= self.breakout_level * 1.002:
                    self.is_long = True
                    return True
                    
        # Bearish Retest
        recent_lows = lows[-(self.window+20):-1]
        for i in range(len(recent_lows) - self.window - 1, len(recent_lows) - 5):
            ref_low = np.min(lows[i-self.window:i])
            if lows[i] < ref_low:
                self.breakout_level = ref_low
                if closes[-1] < self.breakout_level and highs[-1] >= self.breakout_level * 0.998:
                    self.is_short = True
                    return True

        return False

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Require a reversal candle off the level
        last = candles[-1]
        if self.is_long:
            return last.close > last.open # Bullish close off retest
        else:
            return last.close < last.open # Bearish close off retest

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        if self.is_long:
            return self.breakout_level - (1.0 * atr)
        else:
            return self.breakout_level + (1.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        # Targets are usually the recent high/low before the pullback
        if self.is_long:
            return entry + (4.0 * atr)
        else:
            return entry - (4.0 * atr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        # Higher score if the breakout was strong (ADX > 25)
        features = TechnicalFeatureEngine.get_candle_features(candles)
        adx = features["adx"][-1]
        score = min(1.0, adx / 40.0)
        
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        if rr < 1.5: return None
        
        # Check specific direction alignment
        if mtf_state:
             trade_dir = 1 if self.is_long else -1
             bias_dir = 1 if mtf_state.bias == "bullish" else -1 if mtf_state.bias == "bearish" else 0
             if trade_dir != bias_dir: return None

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
