from typing import List, Optional, Dict
from src.strategies.mean_reversion.engine import MeanReversionLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class RSIExtremeReversion(MeanReversionLifecycleEngine):
    """
    Mean reversion strategy focusing purely on RSI overextension (e.g. RSI > 80 or < 20).
    """
    def __init__(self, spec: InstrumentSpec, threshold_upper: float = 80, threshold_lower: float = 20):
        super().__init__("RSIExtremeReversion", spec)
        self.threshold_upper = threshold_upper
        self.threshold_lower = threshold_lower

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        rsi = features["rsi"][-1]
        
        setup_valid = rsi >= self.threshold_upper or rsi <= self.threshold_lower
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Confirmation by RSI hooking back into the 30-70 range
        features = TechnicalFeatureEngine.get_candle_features(candles)
        rsi = features["rsi"]
        
        if rsi[-2] >= self.threshold_upper and rsi[-1] < self.threshold_upper:
             self.current_phase = StrategyPhase.ENTRY_TRIGGERED
             return True
        elif rsi[-2] <= self.threshold_lower and rsi[-1] > self.threshold_lower:
             self.current_phase = StrategyPhase.ENTRY_TRIGGERED
             return True
             
        return False
