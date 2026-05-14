from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class SMCPullback(BaseStrategy):
    """
    Simplified Smart Money Concepts strategy.
    Detects Break of Structure (BoS) and entries on the Order Block (OB).
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("SMCPullback", StrategyFamily.PULLBACK, spec)

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.TREND, RegimeType.PULLBACK_CONTINUATION, RegimeType.MID_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 20: return False
        
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        
        # HTF Bias Alignment
        if mtf_state:
             # Basic BoS detection
             is_bull_bos = closes[-1] > np.max(highs[-20:-5])
             is_bear_bos = closes[-1] < np.min(lows[-20:-5])
             
             if is_bull_bos and mtf_state.bias != "bullish": return False
             if is_bear_bos and mtf_state.bias != "bearish": return False

        # 1. Break of Structure (BoS)
        # For long: Price closes above previous swing high
        # For short: Price closes below previous swing low
        
        prev_swing_high = np.max(highs[-20:-5])
        prev_swing_low = np.min(lows[-20:-5])
        
        self.is_long = closes[-1] > prev_swing_high
        self.is_short = closes[-1] < prev_swing_low
        
        # 2. Identify the "Order Block" (The last candle in opposite direction before BoS move)
        # This is simplified: we look for the OB level
        if self.is_long:
            self.ob_level = prev_swing_low # Simplified OB floor
        else:
            self.ob_level = prev_swing_high # Simplified OB ceiling
            
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # We enter when price returns to the OB level
        # In this simplified version, we'll just signal the BoS as the setup
        return True

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        return entry - (2.0 * atr) if self.is_long else entry + (2.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        entry = candles[-1].close
        stop = self.define_stop(candles)
        return entry + (4.0 * abs(entry - stop)) if self.is_long else entry - (4.0 * abs(entry - stop))

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.8
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = 0.95
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
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
