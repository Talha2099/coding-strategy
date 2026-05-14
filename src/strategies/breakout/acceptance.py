from typing import List, Optional, Dict
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class AcceptanceBreakout(BreakoutLifecycleEngine):
    """
    Triggers when price 'accepts' a level by consolidating near it
    with rising volume or narrowing range, then breaks.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("AcceptanceBreakout", spec, "acceptance")

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < 20: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Acceptance near breakout high/low
        acceptance = features["acceptance_high"][-1]
        dist_up = abs(features["breakout_dist_upper"][-1])
        dist_low = abs(features["breakout_dist_lower"][-1])
        
        # Consolidation near the edge (last 5 candles spending time there)
        near_edge = dist_up < 0.2 or dist_low < 0.2
        is_accepting = (acceptance > 0.7 and dist_up < 0.3) or (acceptance < 0.3 and dist_low < 0.3)
        
        # 2. Narrowing relative range showing 'pressure'
        range_tight = features["bb_width"][-1] < features["bb_width"][-10]
        
        valid = near_edge and is_accepting and range_tight
        if valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # Ignition trigger: Price breaks the consolidation with volume
        vol_surge = features["rel_vol"][-1] > 1.2
        broken = last.close > features["donchian_upper"][-2] or last.close < features["donchian_lower"][-2]
        
        if broken and vol_surge:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            return True
        return False
