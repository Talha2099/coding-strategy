from typing import List, Optional, Dict
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec
import numpy as np

class BollingerRangeFade(RangeTradingLifecycleEngine):
    """
    Fades Bollinger Band extremes when bands are stable (low expansion) and price shows rejection.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("BollingerRangeFade", spec, "bollinger_edge")

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        last = candles[-1]
        
        # 1. BB Edge proximity
        bb_upper = features["bb_upper"][-1]
        bb_lower = features["bb_lower"][-1]
        
        near_upper = last.high >= bb_upper * 0.998
        near_lower = last.low <= bb_lower * 1.002
        
        # 2. RSI Overextended (adding confidence)
        rsi = features["rsi"][-1]
        rsi_extreme = rsi > 70 or rsi < 30
        
        valid = (near_upper or near_lower) and rsi_extreme
        
        if valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return valid
