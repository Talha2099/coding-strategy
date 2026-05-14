from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class ZScoreMeanReversion(BaseStrategy):
    """
    Mean reversion strategy using Z-Score to identify statistical overextension.
    """
    def __init__(self, spec: InstrumentSpec, threshold: float = 2.0):
        super().__init__("ZScoreMeanReversion", StrategyFamily.MEAN_REVERSION, spec)
        self.threshold = threshold

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.MEAN_REVERTING, RegimeType.RANGE, RegimeType.VOLATILE_UNSTABLE, RegimeType.LATE_TREND]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 30: return False
        
        # HTF Trend check - disable if HTF is trending strongly
        if mtf_state and mtf_state.confluence_score > 0.8:
            return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = features["zscore"][-1]
        
        self.is_short = zscore > self.threshold
        self.is_long = zscore < -self.threshold
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Confirmation by zscore starting to reverse (hooking back)
        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = features["zscore"]
        if self.is_long:
            return zscore[-1] > zscore[-2] # Hooking up
        else:
            return zscore[-1] < zscore[-2] # Hooking down

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        return entry - (2.0 * atr) if self.is_long else entry + (2.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        return features["sma_20"][-1] # Target the mean

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        # Higher score for higher absolute z-score
        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = abs(features["zscore"][-1])
        score = min(1.0, zscore / 4.0)
        
        if mtf_state and mtf_state.bias == "neutral":
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        if rr < 1.0: return None

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
