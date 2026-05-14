from typing import List, Optional, Dict
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class GapAndGo(BaseStrategy):
    """
    Trades gap continuation on session open.
    Requires the gap to be sustained in the first few minutes.
    """
    def __init__(self, spec: InstrumentSpec, min_gap_pct: float = 0.005):
        super().__init__("GapAndGo", StrategyFamily.GAP, spec)
        self.min_gap_pct = min_gap_pct

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.GAP_DRIVEN, RegimeType.BREAKOUT, RegimeType.EARLY_TREND]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 2: return False
        
        last = candles[-1]
        prev = candles[-2]
        
        gap = (last.open - prev.close) / (prev.close + 1e-9)
        self.gap_val = gap

        # HTF Alignment
        if mtf_state:
             direction = "long" if gap > 0 else "short"
             if direction == "long" and mtf_state.bias == "bearish": return False
             if direction == "short" and mtf_state.bias == "bullish": return False
        
        # Detect large gap
        return abs(gap) >= self.min_gap_pct

    def confirm_entry(self, candles: List[Candle]) -> bool:
        if not candles: return False
        last = candles[-1]
        # First bar must close in direction of gap (momentum confirmation)
        if self.gap_val > 0:
            return last.close > last.open and last.close > last.high - (last.high - last.low) * 0.3
        else:
            return last.close < last.open and last.close < last.low + (last.high - last.low) * 0.3

    def define_stop(self, candles: List[Candle]) -> float:
        last = candles[-1]
        # Stop at the extreme of the first candle or mid-gap
        return last.low if self.gap_val > 0 else last.high

    def define_target(self, candles: List[Candle]) -> float:
        entry = candles[-1].close
        stop = self.define_stop(candles)
        risk = abs(entry - stop)
        return entry + (2.5 * risk) if self.gap_val > 0 else entry - (2.5 * risk)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        # Score based on relative gap size
        score = min(0.9, abs(self.gap_val) * 100)
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = min(1.0, score + 0.05)
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        last = candles[-1]
        entry_price = last.close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        
        # Calculate RR
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction="long" if self.gap_val > 0 else "short",
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            holding_period_hint="intraday",
            timestamp=last.ts
        )
