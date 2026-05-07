from typing import List, Optional
import numpy as np
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class VolatilityCompressionBreakout(BaseStrategy):
    """
    Detects low volatility periods (BB Squeeze) followed by a breakout.
    """
    def __init__(self, spec: InstrumentSpec, squeeze_window: int = 20, threshold: float = 0.02):
        super().__init__("VolatilityCompression", StrategyFamily.BREAKOUT, spec)
        self.squeeze_window = squeeze_window
        self.threshold = threshold

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < self.squeeze_window + 5: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        upper = features["bb_upper"]
        lower = features["bb_lower"]
        sma = features["sma_20"]
        closes = features["close"]
        
        # 1. BB Width (Volatility measure)
        bb_width = (upper - lower) / sma
        
        # 2. Check for squeeze in the recent past
        was_squeezed = any(w < self.threshold for w in bb_width[-self.squeeze_window:-1])
        
        # 3. Expansion + Breakout
        is_breaking_up = closes[-1] > upper[-1] and bb_width[-1] > bb_width[-2]
        is_breaking_down = closes[-1] < lower[-1] and bb_width[-1] > bb_width[-2]
        
        return was_squeezed and (is_breaking_up or is_breaking_down)

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        upper = features["bb_upper"]
        lower = features["bb_lower"]
        atr = features["atr"][-1]
        
        direction = "long" if closes[-1] > upper[-1] else "short"
        entry_price = closes[-1]
        
        # Stop at the other band or 2*ATR
        if direction == "long":
            stop_loss = max(lower[-1], entry_price - (2 * atr))
            target = entry_price + (2 * (entry_price - stop_loss))
        else:
            stop_loss = min(upper[-1], entry_price + (2 * atr))
            target = entry_price - (2 * (stop_loss - entry_price))

        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class.value,
            strategy_name=self.name,
            strategy_family=self.family,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=target,
            risk_reward_ratio=2.0,
            confidence_score=0.75,
            regime_tag=regime,
            holding_period_hint="swing",
            timestamp=candles[-1].ts
        )
