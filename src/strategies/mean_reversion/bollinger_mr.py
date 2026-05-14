from typing import List, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class BollingerMeanReversion(BaseStrategy):
    """
    Fades Bollinger Band extremes when RSI is overextended and volatility is stable.
    Targets the mean (SMA 20).
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("BollingerMeanReversion", StrategyFamily.MEAN_REVERSION, spec)

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.MEAN_REVERTING, RegimeType.RANGE, RegimeType.LATE_TREND]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 30: return False
        
        # HTF Trend check - disable if HTF is trending strongly
        if mtf_state and mtf_state.confluence_score > 0.8:
            return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        closes = features["close"]
        bb_upper = features["bb_upper"]
        bb_lower = features["bb_lower"]
        rsi = features["rsi"]
        
        curr_price = closes[-1]
        
        # Overbought and touching upper band
        self.is_short = rsi[-1] > 70 and curr_price >= bb_upper[-1]
        # Oversold and touching lower band
        self.is_long = rsi[-1] < 30 and curr_price <= bb_lower[-1]
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Confirmation by rejection wick or candle color change
        last_candle = candles[-1]
        if self.is_long:
            return last_candle.close > last_candle.open # Bullish candle off lower band
        else:
            return last_candle.close < last_candle.open # Bearish candle off upper band

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        
        if self.is_long:
            return entry - (2.0 * atr)
        else:
            return entry + (2.0 * atr)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Target is the middle band (SMA 20)
        return features["sma_20"][-1]

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Better score if volatility (BB width) is normalizing after a spike
        bb_width = features["bb_width"]
        score = 0.6
        if len(bb_width) > 5 and bb_width[-1] < bb_width[-2]:
            score = 0.8
            
        if mtf_state and mtf_state.bias == "neutral":
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        
        # Calculate RR
        rr = abs(take_profit - entry_price) / (abs(entry_price - stop_loss) + 1e-9)
        
        if rr < 1.1: return None # Require decent RR for mean reversion

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
