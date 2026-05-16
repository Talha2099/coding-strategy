import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.utils.logger import system_logger

class FeatureValidationEngine:
    """
    STAGE G: Feature Validation and Drift Monitoring.
    Ensures features are within valid ranges and tracks statistical drift.
    """
    
    def __init__(self):
        self.feature_stats: Dict[str, Dict[str, float]] = {}

    def validate(self, features: Dict[str, np.ndarray]) -> Dict[str, bool]:
        """Checks for NaNs, Infs, and extreme outliers."""
        valid_map = {}
        for name, data in features.items():
            if isinstance(data, np.ndarray):
                is_invalid = np.any(np.isnan(data)) or np.any(np.isinf(data))
                valid_map[name] = not is_invalid
                
                if is_invalid:
                    system_logger.log_event("FEATURE_INVALID", {"feature": name})
        return valid_map

    def track_drift(self, name: str, current_value: float):
        """Simple EWMA drift detection."""
        if name not in self.feature_stats:
            self.feature_stats[name] = {"mean": current_value, "var": 1.0}
            return
        
        alpha = 0.01
        old_mean = self.feature_stats[name]["mean"]
        new_mean = (1 - alpha) * old_mean + alpha * current_value
        
        diff = current_value - old_mean
        new_var = (1 - alpha) * self.feature_stats[name]["var"] + alpha * (diff ** 2)
        
        self.feature_stats[name]["mean"] = new_mean
        self.feature_stats[name]["var"] = new_var
        
        # Simple Z-Score for drift
        std = np.sqrt(new_var) + 1e-9
        zscore = (current_value - new_mean) / std
        
        if abs(zscore) > 3.0:
            system_logger.log_event("FEATURE_DRIFT", {"feature": name, "zscore": float(zscore)})
