from typing import List, Optional, Dict, Any
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class RangeTradingLifecycleEngine(BaseStrategy):
    """
    Implements a complete range-trading lifecycle.
    Covers:
    - stable range
    - expanding range
    - weakening boundary defense
    - repeated boundary touch
    - mid-range rotation
    - range false break
    - range-to-breakout transition
    - range breakdown
    """
    def __init__(self, name: str, spec: InstrumentSpec, subtype: str = "classic"):
        super().__init__(name, StrategyFamily.RANGE, spec)
        self.subtype = subtype
        self.current_phase = StrategyPhase.SETUP_DETECTED

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.RANGE, RegimeType.MEAN_REVERTING, RegimeType.VOLATILE_UNSTABLE]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """
        Phase A: Range detection.
        Handles: stable range, repeated boundary touch.
        """
        if len(candles) < 50: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Trendless context (Stable range scenario)
        low_adx = features["adx"][-1] < 20.0
        
        # 2. Volatility Stability
        stable_vol = features["bb_width"][-1] < np.mean(features["bb_width"][-100:]) * 1.2
        
        # 3. Boundary testing (Repeated boundary touch scenario)
        dist_up = features["breakout_dist_upper"][-1]
        dist_low = features["breakout_dist_lower"][-1]
        near_edge = abs(dist_up) < 0.25 or abs(dist_low) < 0.25
        
        setup_valid = low_adx and stable_vol and near_edge
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        """
        Phase B: Edge entry.
        Handles: range false break.
        """
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # 1. Price rejection (False break recovery)
        rejection = features["upper_wick_pct"][-1] > 0.4 or features["lower_wick_pct"][-1] > 0.4
        
        # 2. No breakout pressure
        no_pressure = features["bb_expansion"][-1] == 0
        
        # 3. Directional turn
        dist_up = features["breakout_dist_upper"][-1]
        dist_low = features["breakout_dist_lower"][-1]
        
        is_fading_high = dist_up > -0.1 and last.close < last.open
        is_fading_low = dist_low < 0.1 and last.close > last.open
        
        confirmed = rejection and no_pressure and (is_fading_high or is_fading_low)
        
        if confirmed:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            
        return confirmed

    def invalidate_setup(self, candles: List[Candle], regime_state: RegimeState) -> bool:
        """
        Handles: weakening boundary defense, range-to-breakout transition.
        """
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # Compression signals breakout risk
        is_compressing = features["bb_squeeze"][-1] > 0.8
        
        # Weakening defense: price sticks to the edge with high volume
        near_edge = abs(features["breakout_dist_upper"][-1]) < 0.05 or abs(features["breakout_dist_lower"][-1]) < 0.05
        vol_surge = features["rel_vol"][-1] > 2.0
        
        if is_compressing or (near_edge and vol_surge):
            self.current_phase = StrategyPhase.INVALIDATED
            return True
            
        return False

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        atr = features["atr"][-1]
        if last.close > last.open: # Fade low
             return min(c.low for c in candles[-10:]) - 0.5 * atr
        else: # Fade high
             return max(c.high for c in candles[-10:]) + 0.5 * atr

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        mid = features["bb_mid"][-1]
        return features["bb_upper"][-1] if candles[-1].close < mid else features["bb_lower"][-1]

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Full lifecycle state machine.
        Handles: mid-range rotation, range breakdown.
        """
        if len(candles) < 2: return None
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_close = candles[-1].close
        updates = {}
        mid = features["bb_mid"][-1]
        
        # Transition to Position Open
        if idea.lifecycle_phase == StrategyPhase.ENTRY_TRIGGERED:
             updates['lifecycle_phase'] = StrategyPhase.POSITION_OPEN

        # 1. Mid-range Rotation Profit taking
        is_past_mid = (idea.direction == "long" and last_close > mid) or (idea.direction == "short" and last_close < mid)
        if is_past_mid and not idea.metadata.get('scaled_mid', False):
             updates['scaling_action'] = "reduce"
             updates['scaling_size'] = 0.5
             updates['stop_loss'] = idea.entry_price # Break-even
             updates['metadata'] = {**idea.metadata, 'scaled_mid': True}
             updates['lifecycle_phase'] = StrategyPhase.PARTIAL_EXIT

        # 2. Range breakdown / transition (Adverse breakout)
        abs_breakout = (idea.direction == "long" and last_close < features["bb_lower"][-1]) or \
                       (idea.direction == "short" and last_close > features["bb_upper"][-1])
        
        if abs_breakout or features["bb_expansion"][-1] > 0:
             updates['exit'] = True
             updates['exit_reason'] = "range_breakdown"
             updates['lifecycle_phase'] = StrategyPhase.FAILURE
             return updates

        # 3. Continuation
        if idea.lifecycle_phase == StrategyPhase.POSITION_OPEN and abs(last_close - idea.entry_price) / idea.entry_price > 0.005:
              updates['lifecycle_phase'] = StrategyPhase.CONTINUATION

        return updates if updates else None

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry = candles[-1].close
        stop = self.define_stop(candles)
        target = self.define_target(candles)
        rr = abs(target - entry) / (abs(entry - stop) + 1e-9)
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            timeframe="M5",
            strategy_name=self.name,
            strategy_family=self.family,
            strategy_subtype=self.subtype,
            direction="long" if entry < target else "short",
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            risk_reward_ratio=rr,
            confidence_score=0.8,
            regime_tag=RegimeType(regime_state.regime_type),
            lifecycle_phase=self.current_phase,
            invalidation_price=stop,
            holding_period_hint="range_trade",
            timestamp=candles[-1].ts,
            metadata={}
        )
