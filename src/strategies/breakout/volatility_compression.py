from typing import List, Optional, Dict
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class VolatilityCompressionBreakout(BreakoutLifecycleEngine):
    """
    Identifies 'Squeeze' conditions (low Bollinger width) and trades the expansion.
    """
    def __init__(self, spec: InstrumentSpec, squeeze_threshold: float = 0.05):
        super().__init__("VolatilityCompression", spec, "compression")
        self.squeeze_threshold = squeeze_threshold

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 30: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        is_squeezed = features["bb_squeeze"][-1] > 0.5 or features["bb_width"][-1] < self.squeeze_threshold
        
        if is_squeezed:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return is_squeezed

    def confirm_entry(self, candles: List[Candle]) -> bool:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # Look for the expansion candle piercing the band
        expansion = features["bb_expansion"][-1] > 0
        broken_upper = last.close > features["bb_upper"][-1]
        broken_lower = last.close < features["bb_lower"][-1]
        
        vol_surge = features["rel_vol"][-1] > 1.2
        
        if (broken_upper or broken_lower) and expansion and vol_surge:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            return True
            
        return False
