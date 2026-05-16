from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class RangeFade(RangeTradingLifecycleEngine):
    """
    Standard range fade strategy.
    Uses Hurst exponent filter: Hurst < 0.4 indicates mean-reverting/ranging bias.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("RangeFade", spec, "classic")

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Hurst Exponent Filter
        # Hurst < 0.45 usually indicates anti-persistent (mean-reverting) behavior
        hurst = features["hurst"][-1] if "hurst" in features else 0.5
        is_anti_persistent = hurst < 0.45
        
        # 2. Oscillating context (RSI centered or extreme)
        rsi = features["rsi"][-1]
        is_oscillating = 30 < rsi < 70
        
        valid = is_anti_persistent and is_oscillating
        if valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return valid

    def confirm_entry(self, candles: List[Candle], regime_state: Optional[RegimeState] = None, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        # Standard rejection confirmation from engine
        return super().confirm_entry(candles, regime_state, mtf_state)

