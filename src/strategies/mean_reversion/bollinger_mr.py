from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class BollingerMeanReversion(BaseStrategy):
    """
    Fades Bollinger Band extremes when RSI is overextended.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("BollingerMeanReversion", StrategyFamily.MEAN_REVERSION, spec)

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < 20: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        rsi = features["rsi"]
        
        curr_price = closes[-1]
        
        # Overbought and touching upper band
        if rsi[-1] > 70 and curr_price >= bb_upper[-1]:
            return True
        # Oversold and touching lower band
        if rsi[-1] < 30 and curr_price <= bb_lower[-1]:
            return True
            
        return False

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        sma_20 = features["sma_20"] # BB Mid
        rsi = features["rsi"]
        atr = features["atr"][-1]
        
        direction = "short" if rsi[-1] > 70 else "long"
        entry_price = closes[-1]
        
        target_price = sma_20[-1] # Target is the mid band
        
        if direction == "long":
            stop_loss = entry_price - (2 * atr)
            take_profit = target_price
        else:
            stop_loss = entry_price + (2 * atr)
            take_profit = target_price

        # Calculate RR
        rr = abs(take_profit - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0
        
        if rr < 1.0: return None # Don't take poor RR trades

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
            confidence_score=0.65,
            regime_tag=regime,
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
