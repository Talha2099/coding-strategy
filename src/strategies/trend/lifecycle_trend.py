from typing import List, Optional, Dict
from datetime import datetime
from src.core.types.trading import Candle, RegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.contracts.spec import InstrumentSpec
from src.strategies.base import BaseStrategy
from src.features.technical_engine import TechnicalFeatureEngine
import numpy as np

class LifecycleTrendStrategy(BaseStrategy):
    """
    Comprehensive Trend Following system that manages the full lifecycle (Stages 0-7).
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("LifecycleTrend", StrategyFamily.TREND, spec)
        self.lookback = 200

    def is_valid_regime(self, regime: RegimeType) -> bool:
        # We handle most regimes in a specific way in lifecycle trading
        return regime in [
            RegimeType.TREND_UP, RegimeType.TREND_DOWN,
            RegimeType.EARLY_TREND, RegimeType.MID_TREND,
            RegimeType.LATE_TREND, RegimeType.PULLBACK_IN_TREND,
            RegimeType.BREAKOUT_PREP
        ]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 50: return False
        
        # Phase 6: Late-trend protection
        if regime_state.exhaustion_risk > 0.7 or regime_state.overextension > 2.5:
            return False
            
        if regime_state.health_score < 0.4:
            return False

        regime = RegimeType(regime_state.regime_type)
        stage = regime_state.lifecycle_stage
        features = TechnicalFeatureEngine.get_candle_features(candles)

        # Multi-Timeframe Alignment
        if mtf_state:
            slope = features["sma_20_slope"][-1]
            direction = "long" if slope > 0 else "short"
            
            # HTF directional check
            htf_dir = mtf_state.htf_state.direction
            if direction == "long" and htf_dir == -1: return False
            if direction == "short" and htf_dir == 1: return False
        
        # 1. EARLY IGNITION (Stage 1 or 2)
        if stage in [1, 2]:
            # Trigger: Price broke range boundaries or EMA stack started
            is_hh = features["is_hh"][-1] > 0.5
            is_ll = features["is_ll"][-1] > 0.5
            adx = features["adx"][-1]
            if (is_hh or is_ll) and adx > 25:
                return True
        
        # 2. MID-TREND CONTINUATION (Stage 3)
        if stage == 3:
            # Momentum resumption after minor pause
            # Check if RSI is returning from neutral to trend zone
            rsi = features["rsi"][-1]
            prev_rsi = features["rsi"][-2]
            sma_slope = features["sma_20_slope"][-1]
            
            if sma_slope > 0 and prev_rsi < 60 and rsi >= 60:
                return True
            if sma_slope < 0 and prev_rsi > 40 and rsi <= 40:
                return True
                
        # 3. PULLBACK CONTINUATION (Stage 4)
        if stage == 4:
            # We are in a pullback. Wait for "Ignition" within the pullback
            # e.g. a candle in the trend direction
            last = candles[-1]
            slope = features["sma_20_slope"][-1]
            if slope > 0 and last.close > last.open: # Bullish candle in uptrend pullback
                return True
            if slope < 0 and last.close < last.open: # Bearish candle in downtrend pullback
                return True

        return False

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Require follow-through candle or decent body size
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        body_pct = features["body_pct"][-1]
        
        # Avoid entries on "indecision" candles (small bodies)
        return body_pct > 0.3

    def define_stop(self, candles: List[Candle], stage: int) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        close = candles[-1].close
        slope = features["sma_20_slope"][-1]
        
        # Sizing stops by stage
        multiplier = 2.0
        if stage in [1, 2]: multiplier = 1.5 # Tighter on ignition
        if stage == 4: multiplier = 1.2 # Tight on pullback entry
        if stage >= 5: multiplier = 2.5 # Looser to survive late volatility
        
        if slope > 0:
            return close - (atr * multiplier)
        else:
            return close + (atr * multiplier)

    def define_target(self, candles: List[Candle], stage: int) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        close = candles[-1].close
        slope = features["sma_20_slope"][-1]
        
        # RR expectations by stage
        rr = 3.0
        if stage in [1, 2]: rr = 4.0 # High potential early
        if stage >= 5: rr = 1.5 # Quick exit late stage
        
        stop_dist = abs(close - self.define_stop(candles, stage))
        
        if slope > 0:
            return close + (stop_dist * rr)
        else:
            return close - (stop_dist * rr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        adx = features["adx"][-1]
        stage = regime_state.lifecycle_stage
        
        # Preference for early/mid stages
        base_score = 0.5
        if stage in [1, 2]: base_score = 0.8
        if stage == 3: base_score = 0.9
        if stage == 4: base_score = 0.7
        if stage >= 5: base_score = 0.4 # Avoid late stage unless high conviction
        
        # Phase 6: Health weighting
        base_score *= (regime_state.health_score + 0.5) # Amplify high health, damp low health
        
        # Confluence bonus
        if mtf_state and mtf_state.confluence_score > 0.8:
            base_score += 0.1

        # ADX weighting
        adx_mult = 1.0
        if 20 < adx < 50: adx_mult = 1.2
        if adx > 60: adx_mult = 0.8 # Overextended
        
        return min(1.0, base_score * adx_mult)

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Detect weakening trend strength and trigger tighter stops or partial exits.
        """
        if len(candles) < 2: return None
        features = TechnicalFeatureEngine.get_candle_features(candles)
        stage = regime_state.lifecycle_stage
        
        # MTF Context check: If HTF bias flips, exit early
        if mtf_state:
             bias_dir = 1 if mtf_state.bias == "bullish" else -1 if mtf_state.bias == "bearish" else 0
             trade_dir = 1 if idea.direction == "long" else -1
             if bias_dir == -trade_dir:
                  return {"exit": True, "metadata": {"update_reason": "HTF_BIAS_FLIP"}}

        # Sizing / Update logic
        # 1. Health-based Trailing
        if regime_state.health_score < 0.5:
             # Tighten stops significantly when trend stability fails
             return {"stop_loss": self.define_stop(candles, 6), "metadata": {"update_reason": "HEALTH_DETERIORATION"}}

        if regime_state.exhaustion_risk > 0.8:
             # Take partial profit or exit if exhaustion is critical
             return {"exit": True, "metadata": {"update_reason": "EXHAUSTION_LIMIT"}}

        # 2. Late Stage Protection (Stage 6 or 7)
        if stage >= 6:
             # Trail stop very tightly (Stage 7 definition)
             return {"stop_loss": self.define_stop(candles, 7), "metadata": {"update_reason": "LATE_STAGE_PROTECTION"}}

        # 2. ADX Rollover in Late Trend
        adx = features["adx"][-1]
        prev_adx = features["adx"][-2]
        if adx < prev_adx and adx < 30 and stage >= 5:
             return {"stop_loss": self.define_stop(candles, 6), "metadata": {"update_reason": "ADX_ROLLOVER"}}
             
        # 3. Overextension Protection
        zscore = features["zscore"][-1]
        if abs(zscore) > 3.5:
            # Shift stop to break-even to lock in risk-free trade
            current_sl = idea.stop_loss
            proposed_sl = idea.entry_price
            
            # Ensure we only move stop IN our direction
            if idea.direction == "long" and proposed_sl > current_sl:
                 return {"stop_loss": proposed_sl, "metadata": {"update_reason": "OVEREXTENSION_LOCK"}}
            elif idea.direction == "short" and proposed_sl < current_sl:
                 return {"stop_loss": proposed_sl, "metadata": {"update_reason": "OVEREXTENSION_LOCK"}}

        return None

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        regime = RegimeType(regime_state.regime_type)
        if not self.is_valid_regime(regime): return None
        if not self.detect_setup(candles, regime_state, mtf_state): return None
        if not self.confirm_entry(candles): return None
        
        features = TechnicalFeatureEngine.get_candle_features(candles)
        slope = features["sma_20_slope"][-1]
        direction = "long" if slope > 0 else "short"
        stage = regime_state.lifecycle_stage
        
        entry = candles[-1].close
        sl = self.define_stop(candles, stage)
        tp = self.define_target(candles, stage)
        rr = abs(tp - entry) / (abs(entry - sl) + 1e-9)
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            strategy_name=self.name,
            strategy_family=self.family,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=regime,
            holding_period_hint="swing",
            timestamp=candles[-1].ts,
            metadata={
                "lifecycle_stage": stage,
                "adx": features["adx"][-1],
                "atr": features["atr"][-1],
                "slope": slope,
                "mtf_bias": mtf_state.bias if mtf_state else "none"
            }
        )
