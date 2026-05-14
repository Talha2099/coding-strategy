from typing import List, Optional, Dict
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class OpeningRangeBreakout(BreakoutLifecycleEngine):
    """
    Strategy that trades breakouts of the first N minutes of the session.
    """
    def __init__(self, spec: InstrumentSpec, range_minutes: int = 15):
        super().__init__("OpeningRangeBreakout", spec, "orb")
        self.range_minutes = range_minutes
        self.orb_high = None
        self.orb_low = None

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        # Determine the opening range for today
        today = candles[-1].ts.date()
        today_candles = [c for c in candles if c.ts.date() == today]
        
        if len(today_candles) < self.range_minutes: return False
        
        range_candles = today_candles[:self.range_minutes]
        self.orb_high = max(c.high for c in range_candles)
        self.orb_low = min(c.low for c in range_candles)
        
        if len(today_candles) <= self.range_minutes: return False
        
        # Setup is true once range is formed and we are near the boundaries
        last = candles[-1]
        near_edge = abs(last.close - self.orb_high) < (self.orb_high - self.orb_low) * 0.1 or \
                    abs(last.close - self.orb_low) < (self.orb_high - self.orb_low) * 0.1
        
        if near_edge:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return near_edge

    def confirm_entry(self, candles: List[Candle]) -> bool:
        last = candles[-1]
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        broken = last.close > self.orb_high or last.close < self.orb_low
        vol_surge = features["rel_vol"][-1] > 1.3
        
        if broken and vol_surge:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            return True
        return False
