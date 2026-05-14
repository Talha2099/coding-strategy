from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class SRFade(RangeTradingLifecycleEngine):
    """
    Fades major Support and Resistance levels in ranging markets.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 50):
        super().__init__("SRFade", spec, "sr_levels")
        self.window = window

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Identify levels from Donchian channels (which capture recent extremes)
        donchian_up = features["donchian_upper"][-1]
        donchian_low = features["donchian_lower"][-1]
        
        last = candles[-1]
        
        # 2. Check closeness to extremes
        near_res = abs(last.high - donchian_up) / last.close < 0.001
        near_supp = abs(last.low - donchian_low) / last.close < 0.001
        
        valid = near_res or near_supp
        if valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Uses engine's rejection logic
        return super().confirm_entry(candles)

    def define_stop(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        atr = features["atr"][-1]
        entry = candles[-1].close
        # Tight stop for range fades
        return entry - (1.2 * atr) if entry > candles[-1].open else entry + (1.2 * atr)

