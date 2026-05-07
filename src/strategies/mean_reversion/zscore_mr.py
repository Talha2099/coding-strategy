from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class ZScoreMeanReversion(BaseStrategy):
    """
    Standard statistical mean reversion using Z-Score of price from SMA.
    """
    def __init__(self, spec: InstrumentSpec, z_threshold: float = 2.0):
        super().__init__("ZScoreMR", StrategyFamily.MEAN_REVERSION, spec)
        self.z_threshold = z_threshold

    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        if len(candles) < 20: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = features["zscore"]
        
        # Trigger when z-score crosses the threshold
        curr_z = zscore[-1]
        return abs(curr_z) >= self.z_threshold

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = features["zscore"][-1]
        entry_price = candles[-1].close
        atr = features["atr"][-1]
        
        direction = "short" if zscore > 0 else "long"
        
        # Target is the mean (Z=0)
        target_price = features["sma_20"][-1]
        
        if direction == "long":
            stop_loss = entry_price - (1.5 * atr)
            take_profit = target_price
        else:
            stop_loss = entry_price + (1.5 * atr)
            take_profit = target_price

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
            regime_tag=regime,
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
