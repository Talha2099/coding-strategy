from typing import List, Optional, Dict, Any
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.instrument_spec import InstrumentSpec
from src.core.contracts.strategy_params import BreakoutParams
import numpy as np

class BreakoutLifecycleEngine(BaseStrategy):
    """
    Implements full lifecycle logic for Breakout strategies.
    Covers: 
    - compression breakout
    - false breakout
    - late breakout
    - breakout exhaustion
    - breakout failure and re-entry into range
    """
    def __init__(self, name: str, spec: InstrumentSpec, subtype: str = "classic"):
        super().__init__(name, StrategyFamily.BREAKOUT, spec)
        self.subtype = subtype
        self.current_phase = StrategyPhase.SETUP_DETECTED
        self.ignition_candle = None

    def is_valid_regime(self, regime: RegimeType) -> bool:
        # Breakouts favor range or breakout_prep regimes
        valid = [
            RegimeType.RANGE, 
            RegimeType.BREAKOUT_PREP, 
            RegimeType.EARLY_TREND,
            RegimeType.BREAKOUT_ACTIVE,
            RegimeType.PRE_TREND
        ]
        return regime in valid

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """
        Phase A: Setup detection (Compression).
        Handles: compression breakout scenario.
        """
        params: BreakoutParams = self.get_params()
        if len(candles) < params.lookback_window: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Volatility Compression
        is_squeezed = features["bb_squeeze"][-1] > 0.5
        low_vol = features["realized_vol"][-1] < np.mean(features["realized_vol"][-params.lookback_window:])
        
        # 2. Consolidation Tightness
        range_tight = features["bb_width"][-1] < np.percentile(features["bb_width"][-100:], 25)
        
        # 3. Acceptance near edges (testing level repeatedly)
        acceptance = features["acceptance_high"][-1]
        testing_upper = acceptance > (1.0 - params.acceptance_barrier) and abs(features["breakout_dist_upper"][-1]) < 0.3
        testing_lower = acceptance < params.acceptance_barrier and abs(features["breakout_dist_lower"][-1]) < 0.3
        
        setup_valid = (is_squeezed or range_tight) and (testing_upper or testing_lower)
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def confirm_entry(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """
        Phase B: Entry Trigger / Ignition.
        """
        params: BreakoutParams = self.get_params()
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # 1. Velocity & Range Expansion
        vol_expansion = features["rel_vol"][-1] > params.rel_vol_threshold
        range_expansion = features["candle_range"][-1] > features["atr"][-1] * 1.1
        
        # 2. Piercing major levels
        broken_upper = last.close > features["bb_upper"][-1] or last.close > features["donchian_upper"][-1]
        broken_lower = last.close < features["bb_lower"][-1] or last.close < features["donchian_lower"][-1]
        
        # 3. Directional dominance (Strong Body)
        strong_body = features["body_pct"][-1] > (params.confirmation_threshold + 0.1)
        
        ignition = (broken_upper or broken_lower) and vol_expansion and strong_body
        
        if ignition:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            
        return ignition

    def invalidate_setup(self, candles: List[Candle], regime_state: RegimeState) -> bool:
        """
        Handles: late breakout scenario.
        """
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        
        # Late Entry Check: If price already moved too far
        dist_up = features["breakout_dist_upper"][-1]
        dist_low = features["breakout_dist_lower"][-1]
        
        if dist_up > 1.5 or dist_low < -1.5:
             self.current_phase = StrategyPhase.INVALIDATED
             return True # Late breakout
             
        # Regime Invalidation
        if regime_state.regime_type == RegimeType.MEAN_REVERTING.value:
             self.current_phase = StrategyPhase.INVALIDATED
             return True
            
        return False

    def define_stop(self, candles: List[Candle]) -> float:
        params: BreakoutParams = self.get_params()
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        atr = features["atr"][-1]
        
        if last.close > last.open: # Long
            return max(features["bb_mid"][-1], last.low - params.stop_multiplier * atr)
        else: # Short
            return min(features["bb_mid"][-1], last.high + params.stop_multiplier * atr)

    def define_target(self, candles: List[Candle]) -> float:
        params: BreakoutParams = self.get_params()
        features = TechnicalFeatureEngine.get_candle_features(candles)
        entry = candles[-1].close
        atr = features["atr"][-1]
        
        multiplier = params.target_multiplier
        return entry + (multiplier * atr) if entry > candles[-1].open else entry - (multiplier * atr)

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        compression_depth = 1.0 - (features["bb_width"][-1] / (np.mean(features["bb_width"][-100:]) + 1e-9))
        vol_surge = min(1.0, features["rel_vol"][-1] / 3.0)
        
        score = (compression_depth * 0.4) + (vol_surge * 0.6)
        if mtf_state and mtf_state.confluence_score > 0.7:
            score += 0.2
        return min(1.0, score)

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Full lifecycle state machine.
        Handles: continuation, breakout exhaustion, failure/false breakout.
        """
        if len(candles) < 2: return None
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_close = candles[-1].close
        
        updates = {}
        
        # Transition from Triggered to Open
        if idea.lifecycle_phase == StrategyPhase.ENTRY_TRIGGERED:
             updates['lifecycle_phase'] = StrategyPhase.POSITION_OPEN
             
        # 1. Trailing Stop (Trailing state)
        if idea.direction == "long":
            new_stop = max(idea.stop_loss, features["ema_20"][-1])
            if new_stop > idea.stop_loss: 
                updates['stop_loss'] = new_stop
                updates['lifecycle_phase'] = StrategyPhase.TRAILING
        else:
            new_stop = min(idea.stop_loss, features["ema_20"][-1])
            if new_stop < idea.stop_loss: 
                updates['stop_loss'] = new_stop
                updates['lifecycle_phase'] = StrategyPhase.TRAILING

        # 2. Exhaustion Detection (Exhaustion state)
        if features["exhaustion_score"][-1] > 0.8:
            updates['exit'] = True
            updates['exit_reason'] = "breakout_exhaustion"
            updates['lifecycle_phase'] = StrategyPhase.EXIT_TRIGGERED
            return updates

        # 3. False Breakout Recovery (Failure state)
        # If price closes deep back inside the range
        mid = features["bb_mid"][-1]
        is_fake = (idea.direction == "long" and last_close < mid) or (idea.direction == "short" and last_close > mid)
        if is_fake:
            updates['exit'] = True
            updates['exit_reason'] = "false_breakout_reentry"
            updates['lifecycle_phase'] = StrategyPhase.FAILURE
            return updates

        # 4. Continuation
        if idea.lifecycle_phase == StrategyPhase.POSITION_OPEN and abs(last_close - idea.entry_price) / idea.entry_price > 0.01:
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
            timeframe="M5", # Proxy
            strategy_name=self.name,
            strategy_family=self.family,
            strategy_subtype=self.subtype,
            direction="long" if entry > candles[-1].open else "short",
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            risk_reward_ratio=rr,
            confidence_score=self.score_setup(candles, regime_state, mtf_state),
            regime_tag=RegimeType(regime_state.regime_type),
            lifecycle_phase=self.current_phase,
            invalidation_price=stop,
            holding_period_hint="intraday",
            timestamp=candles[-1].ts,
            metadata={'vol_expansion': True}
        )
