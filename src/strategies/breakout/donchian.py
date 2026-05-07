from typing import List, Optional
from datetime import datetime
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class DonchianBreakout(BaseStrategy):
    """
    Classic price breakout using Donchian Channels.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 20):
        super().__init__("DonchianBreakout", StrategyFamily.BREAKOUT, spec)
        self.window = window

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < self.window + 1: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        upper = features["donchian_upper"]
        lower = features["donchian_lower"]
        closes = features["close"]
        
        # Current price breaking the PREVIOUS window high/low
        prev_upper = upper[-2]
        prev_lower = lower[-2]
        
        return closes[-1] > prev_upper or closes[-1] < prev_lower

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        upper = features["donchian_upper"]
        lower = features["donchian_lower"]
        atr = features["atr"][-1]
        
        direction = "long" if closes[-1] > upper[-2] else "short"
        entry_price = closes[-1]
        
        # Stop loss at mid of Donchian or 2*ATR
        if direction == "long":
            stop_loss = entry_price - (2 * atr)
            take_profit = entry_price + (4 * atr) # 2.0 RR
        else:
            stop_loss = entry_price + (2 * atr)
            take_profit = entry_price - (4 * atr)

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
            confidence_score=0.7,
            regime_tag=regime,
            holding_period_hint="intraday",
            timestamp=candles[-1].ts
        )
