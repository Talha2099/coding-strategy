from typing import List, Optional, Dict
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class BreakoutRetest(BreakoutLifecycleEngine):
    """
    Waits for a breakout of a major level and then trades the first retest of that level.
    """
    def __init__(self, spec: InstrumentSpec, window: int = 20):
        super().__init__("BreakoutRetest", spec, "retest")
        self.window = window
        self.breakout_level = 0.0

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if len(candles) < self.window + 20: return False
        features = TechnicalFeatureEngine.get_candle_features(candles)
        highs = features["high"]
        lows = features["low"]
        closes = features["close"]
        
        # Identify a broken level in the last 15 bars
        # Look for a spike through donchian or HH/LL that then pulls back
        
        for lookback in range(5, 15):
             # Was it a breakout then?
             if highs[-lookback] > features["donchian_upper"][-lookback-1]:
                  self.breakout_level = features["donchian_upper"][-lookback-1]
                  # Now is it retesting?
                  if lows[-1] <= self.breakout_level * 1.001 and closes[-1] > self.breakout_level:
                       self.current_phase = StrategyPhase.SETUP_DETECTED
                       return True
             elif lows[-lookback] < features["donchian_lower"][-lookback-1]:
                  self.breakout_level = features["donchian_lower"][-lookback-1]
                  if highs[-1] >= self.breakout_level * 0.999 and closes[-1] < self.breakout_level:
                       self.current_phase = StrategyPhase.SETUP_DETECTED
                       return True
                       
        return False

    def confirm_entry(self, candles: List[Candle]) -> bool:
        # Rejection of the retest level
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        is_bull_rejection = last.close > last.open and features["lower_wick_pct"][-1] > 0.3
        is_bear_rejection = last.close < last.open and features["upper_wick_pct"][-1] > 0.3
        
        if is_bull_rejection or is_bear_rejection:
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            self.ignition_candle = last
            return True
        return False
