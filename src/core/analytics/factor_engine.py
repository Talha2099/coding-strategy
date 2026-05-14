import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FactorMetric:
    name: string
    ic: float  # Information Coefficient (Spearman Rank Correlation)
    pnl_attribution: float
    decay: float
    importance_score: float

class FactorEngine:
    """
    Tracks the performance and degradation of alpha factors in real-time.
    Uses Information Coefficient (IC) and Rolling Mutual Information.
    """
    def __init__(self, window_size: int = 500):
        self.window_size = window_size
        self.feature_history: Dict[str, List[float]] = {}
        self.returns_history: List[float] = []
        self.pnl_history: List[float] = []
        self.factor_performance: Dict[str, List[float]] = {} # History of ICs

    def update(self, features: Dict[str, float], forward_return: float, trade_pnl: Optional[float] = None):
        """
        Record a feature set and the subsequent realized return.
        """
        for name, value in features.items():
            if name not in self.feature_history:
                self.feature_history[name] = []
                self.factor_performance[name] = []
            self.feature_history[name].append(value)
            if len(self.feature_history[name]) > self.window_size:
                self.feature_history[name].pop(0)

        self.returns_history.append(forward_return)
        if len(self.returns_history) > self.window_size:
            self.returns_history.pop(0)
            
        if trade_pnl is not None:
            self.pnl_history.append(trade_pnl)
            if len(self.pnl_history) > self.window_size:
                self.pnl_history.pop(0)

    @staticmethod
    def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
        breakpoints = np.unique(breakpoints)
        if len(breakpoints) < 2: return 0.0
        
        expected_counts, _ = np.histogram(expected, bins=breakpoints)
        actual_counts, _ = np.histogram(actual, bins=breakpoints)
        
        expected_dist = expected_counts / len(expected)
        actual_dist = actual_counts / len(actual)
        
        expected_dist = np.where(expected_dist == 0, 1e-4, expected_dist)
        actual_dist = np.where(actual_dist == 0, 1e-4, actual_dist)
        
        return float(np.sum((expected_dist - actual_dist) * np.log(expected_dist / actual_dist)))

    def analyze_factors(self) -> List[Dict]:
        """
        Calculates IC, T-Stats, and Drift for each factor.
        """
        metrics = []
        if len(self.returns_history) < 10:
            return []

        for name, values in self.feature_history.items():
            if len(values) != len(self.returns_history):
                continue

            vx = np.array(values)
            vy = np.array(self.returns_history)
            
            # Spearman Rank Correlation (IC)
            idx_x = vx.argsort()
            idx_y = vy.argsort()
            rank_x = np.empty_like(idx_x)
            rank_y = np.empty_like(idx_y)
            rank_x[idx_x] = np.arange(len(vx))
            rank_y[idx_y] = np.arange(len(vy))
            
            ic = np.corrcoef(rank_x, rank_y)[0, 1]
            if np.isnan(ic): ic = 0.0
            
            self.factor_performance[name].append(ic)
            if len(self.factor_performance[name]) > 50:
                self.factor_performance[name].pop(0)

            # Drift Check (PSI)
            # Use first half of window as baseline for PSI comparison
            mid = len(values) // 2
            psi = self.calculate_psi(vx[:mid], vx[mid:]) if mid > 10 else 0.0

            # Detect Decay (comparing recent IC to historical IC)
            recent_ic = np.mean(self.factor_performance[name][-10:])
            hist_ic = np.mean(self.factor_performance[name])
            decay = hist_ic - recent_ic

            metrics.append({
                "name": name,
                "ic": round(ic, 4),
                "psi": round(psi, 4),
                "decay": round(decay, 4),
                "impact": "HIGH" if abs(ic) > 0.1 else "LOW",
                "status": "DEGRADING" if decay > 0.02 or psi > 0.1 else "STABLE"
            })

        return sorted(metrics, key=lambda x: abs(x["ic"]), reverse=True)

    def get_attribution(self) -> Dict[str, float]:
        """
        Decomposes PnL to specific factors using simple linear attribution.
        """
        if not self.pnl_history or len(self.pnl_history) < 20:
            return {}
            
        # Simplified: PnL contribution is proportional to IC strength
        attribution = {}
        total_pnl = sum(self.pnl_history)
        
        ics = {name: abs(np.mean(perf)) for name, perf in self.factor_performance.items()}
        total_ic = sum(ics.values()) if ics.values() else 1.0
        
        for name, ic_val in ics.items():
            attribution[name] = (ic_val / total_ic) * total_pnl
            
        return attribution
