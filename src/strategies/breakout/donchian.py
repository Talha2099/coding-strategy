from typing import List, Optional, Dict
from datetime import datetime
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class DonchianBreakout(BaseStrategy):
    """
    Classic price breakout using Donchian Channels with volume and momentum validation.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 20):
        super().__init__("DonchianBreakout", StrategyFamily.BREAKOUT, spec)
        self.window = window

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.BREAKOUT, RegimeType.BREAKOUT_PREP, RegimeType.TREND, RegimeType.EARLY_TREND, RegimeType.MID_TREND, RegimeType.TREND_UP, RegimeType.TREND_DOWN]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.window + 1: return False
        
        # HTF Alignment
        if mtf_state:
             # Skip if bias is firmly against us
             features = TechnicalFeatureEngine.get_candle_features(candles)
             curr_price = candles[-1].close
             upper = features["donchian_upper"]
             lower = features["donchian_lower"]
             
             if curr_price > upper[-2] and mtf_state.bias == "bearish": return False
             if curr_price < lower[-2] and mtf_state.bias == "bullish": return False

        features = TechnicalFeatureEngine.get_candle_features(candles)
        upper = features["donchian_upper"]
        lower = features["donchian_lower"]
        closes = features["close"]
        
        # Cross above/below previous interval extreme
        self.is_long = closes[-1] > upper[-2]
        self.is_short = closes[-1] < lower[-2]
        
        return self.is_long or self.is_short

    def confirm_entry(self, candles: List[Candle]) -> bool:
        if len(candles) < 2: return False
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        rel_vol = features["rel_vol"][-1]
        
        # Volume expansion confirmation
        last_candle = candles[-1]
        body_pct = abs(last_candle.close - last_candle.open) / (last_candle.high - last_candle.low + 1e-9)
        
        # Strong body and relative volume > 1.2
        return body_pct > 0.4 and rel_vol > 1.2

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        mid = features["donchian_mid"][-1]
        
        if self.is_long:
            # High-conviction stop: mid of channel or 2*ATR
            return max(mid, candles[-1].close - (2 * atr))
        else:
            return min(mid, candles[-1].close + (2 * atr))

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        
        if self.is_long:
            return entry + (4 * atr) # 2.0 RR target
        else:
            return entry - (4 * atr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        adx = features["adx"][-1]
        # Stronger ADX = higher breakout conviction
        score = min(1.0, adx / 50.0)
        
        if mtf_state and mtf_state.confluence_score > 0.8:
            score = min(1.0, score + 0.1)
            
        return score

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry_price = candles[-1].close
        stop_loss = self.define_stop(candles)
        take_profit = self.define_target(candles)
        
        rr = abs(take_profit - entry_price) / (abs(stop_loss - entry_price) + 1e-9)
        
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
