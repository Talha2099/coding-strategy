from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class GapFill(BaseStrategy):
    """
    Fades session open gaps expecting a return to the previous close.
    """
    def __init__(self, spec: InstrumentSpec, min_gap_pct: float = 0.003):
        super().__init__("GapFill", StrategyFamily.GAP, spec)
        self.min_gap_pct = min_gap_pct

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < 2: return False
        
        last = candles[-1]
        prev = candles[-2]
        
        gap = (last.open - prev.close) / prev.close
        
        # Detect large gap and rejection of gap direction (e.g. gap up, candle closes bearish)
        is_large_gap = abs(gap) >= self.min_gap_pct
        is_reversal = (gap > 0 and last.close < last.open) or (gap < 0 and last.close > last.open)
        
        return is_large_gap and is_reversal

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        last = candles[-1]
        prev = candles[-2]
        
        direction = "short" if last.open > prev.close else "long"
        entry_price = last.close
        
        # Target is the previous close (filling the gap)
        take_profit = prev.close
        
        # Stop at high/low of the first candle
        if direction == "long":
            stop_loss = last.low
        else:
            stop_loss = last.high

        rr = abs(take_profit - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0
        if rr < 1.0: return None

        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class.value,
            strategy_name=self.name,
            strategy_family=self.family,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
            confidence_score=0.7,
            regime_tag=RegimeType.GAP,
            holding_period_hint="intraday",
            timestamp=last.ts
        )
