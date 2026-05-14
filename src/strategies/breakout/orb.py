from typing import List, Optional
from datetime import datetime
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class OpeningRangeBreakout(BaseStrategy):
    """
    Strategy that trades breakouts of the first N minutes of the session.
    """
    def __init__(self, spec: InstrumentSpec, range_minutes: int = 15):
        super().__init__("OpeningRangeBreakout", StrategyFamily.BREAKOUT, spec)
        self.range_minutes = range_minutes
        self.orb_high = None
        self.orb_low = None

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.BREAKOUT, RegimeType.TREND, RegimeType.GAP_DRIVEN, RegimeType.EARLY_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.range_minutes: return False
        
        # HTF Alignment
        if mtf_state:
            # We skip if HTF bias is against us
            curr_candle = candles[-1]
            range_candles = candles[-self.range_minutes:] # Approximation
            orb_high = max(c.high for c in range_candles)
            orb_low = min(c.low for c in range_candles)
            
            if curr_candle.close > orb_high and mtf_state.bias == "bearish": return False
            if curr_candle.close < orb_low and mtf_state.bias == "bullish": return False

        # Determine the opening range for today
        today = candles[-1].ts.date()
        today_candles = [c for c in candles if c.ts.date() == today]
        
        if len(today_candles) < self.range_minutes: return False
        
        # First N candles define the range
        range_candles = today_candles[:self.range_minutes]
        self.orb_high = max(c.high for c in range_candles)
        self.orb_low = min(c.low for c in range_candles)
        
        # We only look for breakouts AFTER the range is established
        current_candle = today_candles[-1]
        if len(today_candles) <= self.range_minutes:
            return False
            
        self.is_long = current_candle.close > self.orb_high
        self.is_short = current_candle.close < self.orb_low
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Confirm with momentum or specific candle close
        return True # Simplified for now

    def define_stop(self, candles: List[Candle]) -> float:
        # Stop at the other side of the opening range
        if self.is_long:
            return self.orb_low
        else:
            return self.orb_high

    def define_target(self, candles: List[Candle]) -> float:
        # Target based on range size (1.0 or 2.0 range size)
        range_size = self.orb_high - self.orb_low
        if self.is_long:
            return self.orb_high + (range_size * 2)
        else:
            return self.orb_low - (range_size * 2)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.8 # ORB is high conviction in right regimes
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = 0.9
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
