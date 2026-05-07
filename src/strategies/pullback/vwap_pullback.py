from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class VWAPPullback(BaseStrategy):
    """
    Buys dips to VWAP in uptrends, sells rallies in downtrends.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("VWAPPullback", StrategyFamily.PULLBACK, spec)

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < 20: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        vwap = features["vwap"]
        sma_50 = features["sma_50"]
        
        curr_price = closes[-1]
        curr_vwap = vwap[-1]
        
        # Bull Trend Check
        is_bull = curr_price > sma_50[-1]
        is_near_vwap = abs(curr_price - curr_vwap) < (curr_vwap * 0.001) # Within 0.1% of VWAP
        
        # Rejection candle (Hammer/Wick near VWAP)
        last_candle = candles[-1]
        candle_range = last_candle.high - last_candle.low
        body_size = abs(last_candle.close - last_candle.open)
        is_rejection = (candle_range > 0) and (body_size / candle_range < 0.4)
        
        return is_near_vwap and is_rejection

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        sma_50 = features["sma_50"]
        atr = features["atr"][-1]
        
        direction = "long" if closes[-1] > sma_50[-1] else "short"
        entry_price = closes[-1]
        
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
            confidence_score=0.75,
            regime_tag=regime,
            holding_period_hint="intraday",
            timestamp=candles[-1].ts
        )
