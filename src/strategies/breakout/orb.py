from typing import List, Optional
from datetime import time
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class OpeningRangeBreakout(BaseStrategy):
    """
    Trades the breakout of the first 15 minutes of the London or NY session.
    """
    def __init__(self, spec: InstrumentSpec, range_minutes: int = 15):
        super().__init__("ORB", StrategyFamily.BREAKOUT, spec)
        self.range_minutes = range_minutes
        self.session_started = False
        self.range_high = -1.0
        self.range_low = -1.0
        self.setup_complete = False

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if not candles: return False
        
        # Simple London/NY Open logic
        ts = candles[-1].ts
        is_london_open = ts.hour == 8 and ts.minute <= 30
        is_ny_open = ts.hour == 14 and ts.minute <= 30 # NY open in UTC (approx)
        
        if not (is_london_open or is_ny_open):
            self.session_started = False
            self.setup_complete = False
            return False

        # Build range during first N minutes
        if not self.session_started:
            self.session_started = True
            self.start_ts = ts
            self.range_high = candles[-1].high
            self.range_low = candles[-1].low
            return False

        minutes_in = (ts - self.start_ts).total_seconds() / 60
        if minutes_in < self.range_minutes:
            self.range_high = max(self.range_high, candles[-1].high)
            self.range_low = min(self.range_low, candles[-1].low)
            return False
        
        self.setup_complete = True
        
        # Trigger on breakout of the range
        curr_price = candles[-1].close
        if curr_price > self.range_high or curr_price < self.range_low:
            return True
        
        return False

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        if not self.setup_complete: return None
        
        last = candles[-1]
        direction = "long" if last.close > self.range_high else "short"
        entry_price = last.close
        
        # Stop at the opposite end of the range
        if direction == "long":
            stop_loss = self.range_low
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 2)
        else:
            stop_loss = self.range_high
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 2)

        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class.value,
            strategy_name=self.name,
            strategy_family=self.family,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.0,
            confidence_score=0.85,
            regime_tag=RegimeType.BREAKOUT,
            holding_period_hint="intraday",
            timestamp=last.ts
        )
