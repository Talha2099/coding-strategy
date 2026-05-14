from typing import List, Optional, Dict, Any
from src.strategies.base import BaseStrategy
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class MeanReversionLifecycleEngine(BaseStrategy):
    """
    Implements full lifecycle logic for Mean Reversion.
    Covers: 
    - stretched away from mean
    - extreme volatility spike
    - rejection from extension
    - partial/full mean reversion
    - mean reversion failure during trend
    """
    def __init__(self, name: str, spec: InstrumentSpec):
        super().__init__(name, StrategyFamily.MEAN_REVERSION, spec)
        self.current_phase = StrategyPhase.SETUP_DETECTED

    def is_valid_regime(self, regime: RegimeType) -> bool:
        valid_regimes = [
            RegimeType.RANGE,
            RegimeType.MEAN_REVERTING,
            RegimeType.TREND_EXHAUSTION,
            RegimeType.LATE_TREND,
            RegimeType.VOLATILE_UNSTABLE
        ]
        return regime in valid_regimes

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """
        Phase A: Setup formation.
        Handles: stretched away from mean, volatility spike.
        """
        if len(candles) < 30: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Statistical Stretch
        zscore = features["zscore"][-1]
        is_stretched = abs(zscore) > 2.2
        
        # 2. RSI Extremes
        rsi = features["rsi"][-1]
        is_extreme = rsi > 72 or rsi < 28
        
        # 3. Volatility Spike
        vol_spike = features["rel_vol"][-1] > 2.0
        
        setup_valid = is_stretched or is_extreme or vol_spike
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        """
        Phase B: Entry Trigger / Rejection.
        Handles: rejection from extension.
        """
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # 1. Price Rejection (Wick analysis)
        z = features["zscore"][-1]
        upper_wick = features["upper_wick_pct"][-1]
        lower_wick = features["lower_wick_pct"][-1]
        
        rejection = (z > 2.0 and upper_wick > 0.4) or (z < -2.0 and lower_wick > 0.4)
        
        confirmed = rejection
        if confirmed:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            
        return confirmed

    def invalidate_setup(self, candles: List[Candle], regime_state: RegimeState) -> bool:
        """
        Handles: mean reversion failure during trend.
        """
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Invalidated if trend picks up speed against us
        if features["adx"][-1] > features["adx"][-2] + 2.5:
             self.current_phase = StrategyPhase.INVALIDATED
             return True
        return False

    def define_stop(self, candles: List[Candle]) -> float:
        last = candles[-1]
        atr = TechnicalFeatureEngine.get_candle_features(candles)["atr"][-1]
        buffer = 0.5 * atr
        return last.low - buffer if last.close > last.open else last.high + buffer

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Target Mid BB or EMA20
        return features["bb_mid"][-1]

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Full lifecycle state machine.
        Handles: partial mean reversion, full mean reversion, failure.
        """
        if len(candles) < 2: return None
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last_close = candles[-1].close
        
        updates = {}
        
        # Transition from Triggered to Open
        if idea.lifecycle_phase == StrategyPhase.ENTRY_TRIGGERED:
             updates['lifecycle_phase'] = StrategyPhase.POSITION_OPEN

        # 1. Full Mean Reversion (Target hit)
        target_dist = abs(last_close - idea.take_profit)
        if target_dist < abs(idea.entry_price - idea.take_profit) * 0.1:
             updates['exit'] = True
             updates['exit_reason'] = "full_mean_reversion"
             updates['lifecycle_phase'] = StrategyPhase.CLOSED
             return updates

        # 2. Partial Mean Reversion (Trail Stop)
        pnl_pct = (last_close - idea.entry_price) / idea.entry_price
        if idea.direction == "short": pnl_pct *= -1
        
        if pnl_pct > 0.005: 
             updates['stop_loss'] = idea.entry_price
             updates['lifecycle_phase'] = StrategyPhase.TRAILING

        # 3. Mean Reversion Failure / Trend Takeover
        adx_surge = features["adx"][-1] > 35 and features["adx"][-1] > features["adx"][-2] + 1.0
        if adx_surge and abs(last_close - idea.take_profit) > abs(idea.entry_price - idea.take_profit) * 1.5:
             updates['exit'] = True
             updates['exit_reason'] = "trend_takeover_failure"
             updates['lifecycle_phase'] = StrategyPhase.FAILURE
             return updates

        return updates if updates else None

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        entry = candles[-1].close
        stop = self.define_stop(candles)
        target = self.define_target(candles)
        rr = abs(target - entry) / (abs(entry - stop) + 1e-9)
        z = TechnicalFeatureEngine.get_candle_features(candles)["zscore"][-1]
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            timeframe="M5",
            strategy_name=self.name,
            strategy_family=self.family,
            strategy_subtype="mean_reversion",
            direction="long" if z < 0 else "short",
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            risk_reward_ratio=rr,
            confidence_score=0.8,
            regime_tag=RegimeType(regime_state.regime_type),
            lifecycle_phase=self.current_phase,
            invalidation_price=stop,
            holding_period_hint="scalp",
            timestamp=candles[-1].ts
        )
