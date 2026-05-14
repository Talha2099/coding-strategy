from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class RangeEdgeRotation(RangeTradingLifecycleEngine):
    """
    Trades the rotation from one range edge towards the other.
    Triggered when a rejection is confirmed and momentum starts rolling over.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("RangeEdgeRotation", spec, "rotation")

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        # We look for a recent touch of the opposite edge
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # Check if we were at the opposite edge within the last 15 candles
        dist_up = features["breakout_dist_upper"][-15:]
        dist_low = features["breakout_dist_lower"][-15:]
        
        last_at_top = any(d > -0.1 for d in dist_up)
        last_at_bottom = any(d < 0.1 for d in dist_low)
        
        # Current position check
        curr_dist_up = features["breakout_dist_upper"][-1]
        curr_dist_low = features["breakout_dist_lower"][-1]
        
        at_bottom_now = curr_dist_low < 0.2
        at_top_now = curr_dist_up > -0.2
        
        # Setup is valid if we just rotated from one side to the other approach
        setup_valid = (last_at_top and at_bottom_now) or (last_at_bottom and at_top_now)
        
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Rotation requires a more certain turn
        features = TechnicalFeatureEngine.get_candle_features(candles)
        # RSI crossing its moving average or midpoint
        rsi = features["rsi"]
        rsi_avg = np.mean(rsi[-5:])
        
        # If at bottom, look for RSI cross up
        if candles[-1].close < features["bb_mid"][-1]:
             if rsi[-1] > rsi_avg and rsi[-1] > 45: 
                  self.current_phase = StrategyPhase.ENTRY_TRIGGERED
                  return True
        else: # At top, look for RSI cross down
             if rsi[-1] < rsi_avg and rsi[-1] < 55:
                  self.current_phase = StrategyPhase.ENTRY_TRIGGERED
                  return True
                  
        return False
