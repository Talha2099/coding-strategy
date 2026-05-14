from typing import List, Optional, Dict
from src.strategies.mean_reversion.engine import MeanReversionLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class MAReversion(MeanReversionLifecycleEngine):
    """
    Mean reversion strategy based on price distance from moving averages (EMA 20/50/200).
    Targets the mean (the specific MA being reverted to).
    """
    def __init__(self, spec: InstrumentSpec, window: int = 50):
        super().__init__(f"MAReversion_{window}", spec)
        self.window = window

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # We use distance in ATR units
        atr = features["atr"][-1]
        
        if self.window == 20: ma = features["ema_20"][-1]
        elif self.window == 50: ma = features["ema_50"][-1]
        else: ma = features["ema_20"][-1] # Fallback
        
        dist = (candles[-1].close - ma) / (atr + 1e-9)
        
        # Stretch usually significant above 3 ATR
        setup_valid = abs(dist) > 3.0
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        if self.window == 20: return features["ema_20"][-1]
        if self.window == 50: return features["ema_50"][-1]
        return features["ema_200"][-1]
