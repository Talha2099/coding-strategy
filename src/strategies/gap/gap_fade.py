from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class GapFade(BaseStrategy):
    """
    Fades overnight or session gaps that show signs of exhaustion.
    """
    def __init__(self, spec: InstrumentSpec, min_gap_pct: float = 0.005):
        super().__init__("GapFade", StrategyFamily.GAP, spec)
        self.min_gap_pct = min_gap_pct

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.GAP_DRIVEN, RegimeType.VOLATILE_UNSTABLE, RegimeType.MEAN_REVERTING]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 3: return False
        
        # HTF Context check for fade
        if mtf_state:
             # Fading is often counter-trend, but we prefer HTF range or low confluence
             if mtf_state.confluence_score > 0.8: return False # Strong trend, don't fade gaps against it
             
        last = candles[-1]
        prev = candles[-2]
        
        # Calculate Gap
        gap_val = (last.open - prev.close) / (prev.close + 1e-9)
        self.is_fading_long = gap_val < -self.min_gap_pct # Gap down, fade up
        self.is_fading_short = gap_val > self.min_gap_pct # Gap up, fade down
        
        if not (self.is_fading_long or self.is_fading_short):
            return False
            
        # Look for reversal price action at open
        # e.g. Gap down then a strong bullish candle
        if self.is_fading_long:
            return last.close > last.open and last.close > (last.open + (last.high - last.low) * 0.5)
        if self.is_fading_short:
            return last.close < last.open and last.close < (last.open - (last.high - last.low) * 0.5)
            
        return False

    def confirm_entry(self, candles: List[Candle]) -> bool:
        return True # Price action check is in detect_setup

    def define_stop(self, candles: List[Candle]) -> float:
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Stop at the extreme of the opening candle
        return last.low if self.is_fading_long else last.high

    def define_target(self, candles: List[Candle]) -> float:
        # Target the prior close (Gap Fill)
        return candles[-2].close

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        score = 0.7
        if mtf_state and mtf_state.htf_state.regime_type == RegimeType.RANGE.value:
            score = 0.8
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry = candles[-1].close
        sl = self.define_stop(candles)
        tp = self.define_target(candles)
        rr = abs(tp - entry) / (abs(entry - sl) + 1e-9)
        
        if rr < 1.0: return None
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction="long" if self.is_fading_long else "short",
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            holding_period_hint="intraday",
            timestamp=candles[-1].ts
        )
