import numpy as np
from typing import List, Dict

class DataNormalizer:
    """
    Normalizes raw market data for ML/RL consumption.
    """
    def __init__(self):
        self._means = {}
        self._stds = {}

    def z_score(self, data: np.ndarray, key: str) -> np.ndarray:
        if key not in self._means:
            self._means[key] = np.mean(data)
            self._stds[key] = np.std(data)
        
        return (data - self._means[key]) / (self._stds[key] + 1e-9)

    def min_max(self, data: np.ndarray) -> np.ndarray:
        return (data - np.min(data)) / (np.max(data) - np.min(data) + 1e-9)
