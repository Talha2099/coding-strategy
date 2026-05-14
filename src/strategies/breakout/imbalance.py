from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class ImbalanceBreakout(BaseStrategy):
    """
    Identifies Fair Value Gaps (FVG) and trades breakouts through them.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("ImbalanceBreakout", StrategyFamily.BREAKOUT, spec)

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.BREAKOUT, RegimeType.TREND, RegimeType.EARLY_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 4: return False
        
        # HTF Alignment
        if mtf_state:
             # Skip if FVG is counter to HTF bias
             c1, c2, c3 = candles[-3], candles[-2], candles[-1]
             if c1.high < c3.low and mtf_state.bias == "bearish": return False
             if c1.low > c3.high and mtf_state.bias == "bullish": return False

        # FVG logic: 3 candle pattern
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        self.is_long = c1.high < c3.low
        self.is_short = c1.low > c3.high
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        # Require relative volume > 1.2
        features = TechnicalFeatureEngine.get_candle_features(candles)
        return features["rel_vol"][-1] > 1.2

    def define_stop(self, candles: List[Candle]) -> float:
        # Stop at the other side of the FVG
        c1 = candles[-3]
        return c1.low if self.is_long else c1.high

    def define_target(self, candles: List[Candle]) -> float:
        entry = candles[-1].close
        stop = self.define_stop(candles)
        risk = abs(entry - stop)
        return entry + (3.0 * risk) if self.is_long else entry - (3.0 * risk)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.85
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = 0.95
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
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
            holding_period_hint="intraday",
            timestamp=candles[-1].ts
        )
