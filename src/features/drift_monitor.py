import numpy as np
from typing import Dict, List, Any
from src.core.utils.logger import system_logger

class FeatureDriftMonitor:
    """
    STAGE G: Specialized Drift Monitor for Features.
    Tracks distribution shifts in key features.
    """
    def __init__(self, window: int = 1000):
        self.window = window
        self.history: Dict[str, List[float]] = {}
        
    def record_feature(self, name: str, value: float):
        if name not in self.history:
            self.history[name] = []
        
        self.history[name].append(value)
        if len(self.history[name]) > self.window:
            self.history[name].pop(0)
            
        # Detect shift if we have enough data
        if len(self.history[name]) == self.window:
            first_half = self.history[name][:self.window//2]
            second_half = self.history[name][self.window//2:]
            
            # 1. PSI-like shift (Mean shift in units of std)
            mu1, std1 = np.mean(first_half), np.std(first_half)
            mu2, std2 = np.mean(second_half), np.std(second_half)
            
            shift = abs(mu2 - mu1) / (std1 + 1e-9)
            
            # 2. Distribution overlap (KL divergence proxy)
            # If standard deviations change significantly, distribution has shifted
            vol_shift = abs(std2 - std1) / (std1 + 1e-9)

            if shift > 0.5 or vol_shift > 0.5:
                system_logger.log_event("FEATURE_DRIFT_DETECTED", {
                    "feature": name,
                    "mean_shift": float(shift),
                    "vol_shift": float(vol_shift)
                })
            
            return {"mean_shift": shift, "vol_shift": vol_shift}
        return {}

    def get_drift_report(self) -> Dict[str, Any]:
        return {name: {"len": len(vals)} for name, vals in self.history.items()}
