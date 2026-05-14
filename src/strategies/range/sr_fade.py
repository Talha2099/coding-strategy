from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class SRFade(BaseStrategy):
    """
    Fades major Support and Resistance levels in ranging markets.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 50):
        super().__init__("SRFade", StrategyFamily.RANGE, spec)
        self.window = window

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.RANGE, RegimeType.MEAN_REVERTING, RegimeType.VOLATILE_UNSTABLE]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.window + 10: return False
        
        # HTF Trend check
        if mtf_state and mtf_state.confluence_score > 0.8:
            return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        highs = features["high"]
        lows = features["low"]
        closes = features["close"]
        
        # Identify major S/R levels from previous data
        self.resistance = np.max(highs[-self.window:-2])
        self.support = np.min(lows[-self.window:-2])
        
        curr_price = closes[-1]
        
        self.is_short = curr_price >= self.resistance * 0.999
        self.is_long = curr_price <= self.support * 1.001
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Rejection candle off the level
        last = candles[-1]
        stats = TechnicalFeatureEngine.get_candle_stats(
            np.array([last.high]), 
            np.array([last.low]), 
            np.array([last.open]), 
            np.array([last.close])
        )
        if self.is_long:
            return stats["lower_wick_pct"][0] > 0.3
        else:
            return stats["upper_wick_pct"][0] > 0.3

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        return entry - (1.0 * atr) if self.is_long else entry + (1.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        # Target the opposite side of the range
        return self.resistance if self.is_long else self.support

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.7
        if mtf_state and mtf_state.bias == "neutral":
            score = 0.85
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        if rr < 1.2: return None

        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction="long" if self.is_long else "short",
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
