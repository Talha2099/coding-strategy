from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class RangeFade(BaseStrategy):
    """
    Fades range boundaries when ADX is low and Bollinger Bands are stable.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("RangeFade", StrategyFamily.RANGE, spec)

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if regime != RegimeType.RANGING or len(candles) < 30:
            return False
            
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        
        curr_price = closes[-1]
        
        # Price is at the very edge of the Bollinger Band in a ranging regime
        at_upper = curr_price >= bb_upper[-1] * 0.998
        at_lower = curr_price <= bb_lower[-1] * 1.002
        
        return at_upper or at_lower

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        sma_20 = features["sma_20"] # Mean
        atr = features["atr"][-1]
        
        direction = "short" if closes[-1] >= bb_upper[-1] * 0.998 else "long"
        entry_price = closes[-1]
        
        # Target is the range midpoint (Mean)
        take_profit = sma_20[-1]
        
        # Tight stop for ranges
        if direction == "long":
            stop_loss = entry_price - (1.0 * atr)
        else:
            stop_loss = entry_price + (1.0 * atr)

        rr = abs(take_profit - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0
        if rr < 1.2: return None

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
            regime_tag=regime,
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
