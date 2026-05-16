import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from src.core.utils.logger import system_logger

class FeatureQualityEngine:
    """
    STAGE J: Feature Selection and Quality Control.
    Evaluates features for stability, redundancy, and predictive decay.
    """
    def __init__(self, window: int = 500):
        self.window = window
        self.quality_registry: Dict[str, Dict[str, float]] = {}

    def analyze_quality(self, features: Dict[str, np.ndarray], target_returns: Optional[np.ndarray] = None) -> Dict[str, Dict[str, float]]:
        """
        Computes quality metrics for a batch of features.
        """
        results = {}
        feature_names = list(features.keys())
        
        # 1. Stability Score (Coefficient of Variation based)
        for name, data in features.items():
            if len(data) < 20: continue
            std = np.std(data[-self.window:])
            mean = np.abs(np.mean(data[-self.window:])) + 1e-9
            stability = 1.0 / (1.0 + (std / mean)) # High stability = low variation relative to mean
            
            # predictive usefulness (causal correlation with past returns as a proxy)
            usefulness = 0.5
            if target_returns is not None:
                # Correlation between feature[t-1] and return[t]
                feat_series = pd.Series(data)
                ret_series = pd.Series(target_returns)
                usefulness = abs(feat_series.shift(1).corr(ret_series))
            
            results[name] = {
                "stability": float(stability),
                "usefulness": float(usefulness),
                "last_value": float(data[-1])
            }

        # 2. Redundancy / Correlation Analysis
        # We only check a subset to avoid O(N^2) explosion
        if len(feature_names) > 1:
            df = pd.DataFrame({k: v[-self.window:] for k, v in features.items() if len(v) >= self.window})
            if not df.empty:
                corr_matrix = df.corr().abs()
                for name in results:
                    if name in corr_matrix.index:
                        # Max correlation with ANY OTHER feature
                        redundancy = corr_matrix.loc[name].drop(name).max()
                        results[name]["redundancy"] = float(redundancy)
                        results[name]["is_redundant"] = float(redundancy > 0.95)

        self.quality_registry = results
        return results

    def get_pruned_features(self, features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Removes features marked as redundant or unstable."""
        pruned = {}
        for name, data in features.items():
            quality = self.quality_registry.get(name, {})
            if quality.get("is_redundant", 0.0) < 1.0 and quality.get("stability", 1.0) > 0.1:
                pruned[name] = data
        return pruned
