from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class AuctionBalanceFade(RangeTradingLifecycleEngine):
    """
    Fades price moves away from the 'High Volume Node' or Mid-range in a balanced profile.
    Uses 'Acceptance High' feature to gauge if a breakout is likely to fail.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("AuctionBalanceFade", spec, "auction")

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        
        # 1. Acceptance High check
        # Acceptance near 1.0 means price is accepted at highs (breakout risk)
        # Acceptance near 0.5 means balanced auction
        acc = features["acceptance_high"][-1]
        is_balanced = 0.35 < acc < 0.65
        
        # 2. Distance from balance node (Mid BB is proxy for Point of Control)
        mid = features["bb_mid"][-1]
        dist_pct = abs(candles[-1].close - mid) / mid
        
        # We want to fade when price has deviated from the balance point
        is_deviated = dist_pct > 0.005 
        
        valid = is_balanced and is_deviated
        if valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Confirmation by seeing acceptance start to fall toward balance
        features = TechnicalFeatureEngine.get_candle_features(candles)
        acc = features["acceptance_high"]
        
        # If price is high, we want acceptance to DECREASE
        if candles[-1].close > features["bb_mid"][-1]:
             if acc[-1] < acc[-2]:
                  self.current_phase = StrategyPhase.ENTRY_TRIGGERED
                  return True
        else: # Price is low, we want 'acceptance of highs' to INCREASE (meaning returning to balance)
             if acc[-1] > acc[-2]:
                  self.current_phase = StrategyPhase.ENTRY_TRIGGERED
                  return True
                  
        return False
