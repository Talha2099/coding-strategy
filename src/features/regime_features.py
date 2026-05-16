import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.types.trading import Candle, RegimeState

class RegimeFeatureEngine:
    """
    STAGE D: Regime-Aware Features.
    Integrates classifier results into the feature vector.
    """
    
    @staticmethod
    def extract(regime_state: Optional[RegimeState], length: int) -> Dict[str, np.ndarray]:
        if not regime_state:
            return {
                "regime_type": np.zeros(length),
                "regime_health": np.full(length, 0.5),
                "regime_volatility": np.zeros(length)
            }
        
        return {
            "regime_type": np.full(length, regime_state.regime_type),
            "regime_health": np.full(length, getattr(regime_state, "health_score", 0.5)),
            "regime_volatility": np.full(length, getattr(regime_state, "volatility", 0.0))
        }
