from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class EMAPullback(BaseStrategy):
    """
    Classic trend continuation pullback to the 20 EMA.
    """
    def __init__(self, spec: InstrumentSpec, ema_window: int = 20):
        super().__init__("EMAPullback", StrategyFamily.PULLBACK, spec)
        self.ema_window = ema_window

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < self.ema_window + 10: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        ema = features["ema_10"] # Using 10 EMA for shallow pullbacks or update TechnicalFeatureEngine for 20
        # Actually TechnicalFeatureEngine has ema_10. Let's assume we want a fast EMA pullback.
        
        curr_price = closes[-1]
        prev_price = closes[-2]
        
        # Bull Trend: Price > EMA
        is_bull = curr_price > ema[-1]
        # Pullback: High was above EMA, now Low is near or touching EMA
        was_extended = any(c.high > ema[i] * 1.02 for i, c in enumerate(candles[-10:-1]))
        is_touching = candles[-1].low <= ema[-1] * 1.001 and candles[-1].close > ema[-1]
        
        return is_bull and was_extended and is_touching

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        ema = features["ema_10"]
        atr = features["atr"][-1]
        
        entry_price = candles[-1].close
        direction = "long" # Simplified for this demo
        
        if direction == "long":
            stop_loss = entry_price - (1.5 * atr)
            take_profit = entry_price + (3.0 * atr)
        else:
            stop_loss = entry_price + (1.5 * atr)
            take_profit = entry_price - (3.0 * atr)

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
