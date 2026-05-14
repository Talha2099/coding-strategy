from typing import List, Optional, Dict
from src.strategies.mean_reversion.engine import MeanReversionLifecycleEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.features.technical_engine import TechnicalFeatureEngine
from src.core.contracts.spec import InstrumentSpec

class ZScoreMeanReversion(MeanReversionLifecycleEngine):
    """
    Mean reversion strategy using Z-Score to identify statistical overextension.
    """
    def __init__(self, spec: InstrumentSpec, threshold: float = 2.2):
        super().__init__("ZScoreMeanReversion", spec)
        self.threshold = threshold

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        if not super().detect_setup(candles, regime_state, mtf_state):
             return False
             
        features = TechnicalFeatureEngine.get_candle_features(candles)
        zscore = features["zscore"][-1]
        
        setup_valid = abs(zscore) > self.threshold
        if setup_valid:
            self.current_phase = StrategyPhase.SETUP_DETECTED
            
        return setup_valid

