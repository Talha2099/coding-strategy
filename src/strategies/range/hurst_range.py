from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class HurstRangeStrategy(RangeTradingLifecycleEngine):
    """
    Range strategy that uses the Hurst Exponent as a primary filter.
    Hurst < 0.5 indicates mean-reverting (ranging).
    Hurst > 0.5 indicates trending.
    """
    def __init__(self, spec: InstrumentSpec, hurst_threshold: float = 0.4):
        super().__init__("HurstRange", spec, "hurst_filter")
        self.hurst_threshold = hurst_threshold

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # Hurst Exponent Check
        current_hurst = features["hurst"][-1]
        
        # If hurst is below threshold, the market is in a stationary/mean-reverting regime
        setup_valid = current_hurst < self.hurst_threshold
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        h = features["hurst"][-1]
        # Lower hurst = higher confidence in range
        score = max(0.0, 1.0 - (h / 0.5))
        return min(1.0, score)
