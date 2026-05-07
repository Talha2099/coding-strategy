from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class GapAndGo(BaseStrategy):
    """
    Trades gap continuation on session open.
    """
    def __init__(self, spec: InstrumentSpec, min_gap_pct: float = 0.005):
        super().__init__("GapAndGo", StrategyFamily.GAP, spec)
        self.min_gap_pct = min_gap_pct

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < 2: return False
        
        last = candles[-1]
        prev = candles[-2]
        
        gap = (last.open - prev.close) / prev.close
        
        # Detect large gap and first 5-min bar closing in direction of gap
        is_large_gap = abs(gap) >= self.min_gap_pct
        is_continuation = (gap > 0 and last.close > last.open) or (gap < 0 and last.close < last.open)
        
        return is_large_gap and is_continuation

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        last = candles[-1]
        prev = candles[-2]
        gap = (last.open - prev.close) / prev.close
        
        direction = "long" if gap > 0 else "short"
        entry_price = last.close
        
        # Stop at gap low/high
        if direction == "long":
            stop_loss = last.low # Low of first candle
            target_dist = (entry_price - stop_loss) * 2
            take_profit = entry_price + target_dist
        else:
            stop_loss = last.high
            target_dist = (stop_loss - entry_price) * 2
            take_profit = entry_price - target_dist

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
            confidence_score=0.8,
            regime_tag=RegimeType.GAP,
            holding_period_hint="intraday",
            timestamp=last.ts
        )
