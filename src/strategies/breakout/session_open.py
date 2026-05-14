from typing import List, Optional, Dict
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class SessionOpenBreakout(BreakoutLifecycleEngine):
    """
    Specifically trades the London or NY session open momentum.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("SessionOpenBreakout", spec, "session_open")
        self.session_hours = [7, 8, 12, 13] # London and NY opens in UTC roughly

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [RegimeType.RANGE, RegimeType.BREAKOUT_PREP, RegimeType.GAP_DRIVEN, RegimeType.VOLATILE_UNSTABLE]

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        last = candles[-1]
        hour = last.ts.hour
        
        # Only trade during the first 30 mins of session opens
        is_opening = hour in self.session_hours
        if not is_opening: return False
        
        # Check for pre-session range narrowing
        features = TechnicalFeatureEngine.get_candle_features(candles)
        compression = features["bb_squeeze"][-1] > 0.0 or features["bb_width"][-1] < np.mean(features["bb_width"][-20:])
        
        if compression:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return compression

    def confirm_entry(self, candles: List[Candle]) -> bool:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # Typical session momentum: Breakout of the prev hour high/low
        prev_hour_high = np.max([c.high for c in candles[-15:-1]]) # Approximation
        prev_hour_low = np.min([c.low for c in candles[-15:-1]])
        
        vol_surge = features["rel_vol"][-1] > 1.5
        broken = last.close > prev_hour_high or last.close < prev_hour_low
        
        if broken and vol_surge:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            return True
        return False
