import numpy as np
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

class DriftMonitor:
    """
    Monitors feature drift and strategy decay using PSI and KL Divergence.
    """
    def __init__(self, baseline_data: Dict[str, np.ndarray]):
        self.baseline = baseline_data
        self.drift_history: List[Dict[str, Any]] = []

    def calculate_psi(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        """
        Population Stability Index.
        PSI < 0.1: No change
        PSI < 0.25: Slight change
        PSI >= 0.25: Significant change
        """
        def get_dist(data, bins):
            counts, _ = np.histogram(data, bins=bins)
            return counts / len(data)

        # Use quantiles from expected to define bins
        breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
        # Ensure unique breakpoints
        breakpoints = np.unique(breakpoints)
        if len(breakpoints) < 2: return 0.0

        expected_dist = get_dist(expected, bins=breakpoints)
        actual_dist = get_dist(actual, bins=breakpoints)

        # Avoid zero division/log errors
        expected_dist = np.where(expected_dist == 0, 1e-4, expected_dist)
        actual_dist = np.where(actual_dist == 0, 1e-4, actual_dist)

        psi = np.sum((expected_dist - actual_dist) * np.log(expected_dist / actual_dist))
        return float(psi)

    def calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Kullback-Leibler Divergence."""
        p = np.where(p == 0, 1e-10, p)
        q = np.where(q == 0, 1e-10, q)
        return float(np.sum(p * np.log(p / q)))

    def check_drift(self, current_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        drift_scores = {}
        for feature, vals in current_data.items():
            if feature in self.baseline:
                psi = self.calculate_psi(self.baseline[feature], vals)
                drift_scores[feature] = psi
        
        self.drift_history.append({
            "ts": datetime.utcnow().isoformat(),
            "scores": drift_scores
        })
        return drift_scores

    def get_decay_signal(self, rolling_sharpe: List[float], window: int = 20) -> float:
        """
        Returns a signal if the rolling Sharpe ratio is significantly decaying.
        1.0 = High Decay, 0.0 = Stable
        """
        if len(rolling_sharpe) < window * 2: return 0.0
        
        recent = np.mean(rolling_sharpe[-window:])
        historical = np.mean(rolling_sharpe[:-window])
        
        if historical <= 0: return 0.0
        
        decay = (historical - recent) / historical
        return float(max(0.0, min(1.0, decay)))
