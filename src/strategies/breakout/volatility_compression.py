from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class VolatilityCompressionBreakout(BaseStrategy):
    """
    Identifies 'Squeeze' conditions (low Bollinger width) and trades the expansion.
    """
    def __init__(self, spec: InstrumentSpec, squeeze_threshold: float = 0.05):
        super().__init__("VolatilityCompression", StrategyFamily.BREAKOUT, spec)
        self.squeeze_threshold = squeeze_threshold

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.BREAKOUT_PREP, RegimeType.RANGE, RegimeType.EARLY_TREND]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 30: return False
        
        # HTF Alignment
        if mtf_state:
             # Skip if expansion is against HTF bias
             features = TechnicalFeatureEngine.get_candle_features(candles)
             closes = features["close"]
             bb_upper = features["bb_upper"]
             bb_lower = features["bb_lower"]
             
             if closes[-1] > bb_upper[-1] and mtf_state.bias == "bearish": return False
             if closes[-1] < bb_lower[-1] and mtf_state.bias == "bullish": return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        bb_width = features["bb_width"]
        
        # Check if we were in a squeeze recently (last 5-10 bars)
        is_squeezed = any(w < self.squeeze_threshold for w in bb_width[-10:-1]) or features["bb_squeeze"][-1] > 0.5
        
        # Now looking for expansion
        expansion = bb_width[-1] > bb_width[-2] * 1.1
        
        closes = features["close"]
        # Note: bb_upper/bb_lower might not be in features dict if only returning derived stats, check engine
        # In current engine bb_upper/bb_lower ARE returned
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        
        self.is_long = closes[-1] > bb_upper[-1]
        self.is_short = closes[-1] < bb_lower[-1]
        
        return is_squeezed and expansion and (self.is_long or self.is_short)

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Require strong directional close
        last = candles[-1]
        body_pct = abs(last.close - last.open) / (last.high - last.low + 1e-9)
        return body_pct > 0.5

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Stop at the other band or mid-band
        return features["bb_lower"][-1] if self.is_long else features["bb_upper"][-1]

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        return entry + (4.0 * atr) if self.is_long else entry - (4.0 * atr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        # Score based on how tight the squeeze was
        features = TechnicalFeatureEngine.get_candle_features(candles)
        min_width = min(features["bb_width"][-10:])
        score = min(1.0, 1.0 / (min_width * 10 + 1e-9))
        
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = min(1.0, score + 0.1)
            
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
