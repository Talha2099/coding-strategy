import numpy as np
from typing import Dict, List, Tuple

class KalmanTrendFilter:
    """
    State-space model for low-lag trend estimation.
    State: [Position, Velocity, Acceleration]
    """
    def __init__(self, process_noise: float = 1e-5, measurement_noise: float = 1e-3):
        self.q = process_noise
        self.r = measurement_noise
        
        # State vector [x, v, a]
        self.state = np.zeros(3)
        self.P = np.eye(3) * 1.0
        
        # Transition matrix (assuming dt=1)
        self.F = np.array([
            [1, 1, 0.5],
            [0, 1, 1],
            [0, 0, 1]
        ])
        
        # Measurement matrix (we only see position)
        self.H = np.array([[1, 0, 0]])

    def update(self, price: float) -> Dict[str, float]:
        # Prediction
        x_pred = self.F @ self.state
        P_pred = self.F @ self.P @ self.F.T + np.eye(3) * self.q
        
        # Correction
        y = price - (self.H @ x_pred)
        S = self.H @ P_pred @ self.H.T + self.r
        K = P_pred @ self.H.T @ np.linalg.inv(S)
        
        self.state = x_pred + (K @ y).flatten()
        self.P = (np.eye(3) - K @ self.H) @ P_pred
        
        return {
            "position": self.state[0],
            "velocity": self.state[1],
            "acceleration": self.state[2],
            "confidence": 1.0 / (1.0 + np.trace(self.P))
        }

class HurstPersistence:
    """
    Differentiates between Trending (H > 0.5) and Mean Reverting (H < 0.5).
    """
    @staticmethod
    def calculate(prices: List[float], lags: List[int] = [2, 4, 8, 16, 32]) -> float:
        if len(prices) < 40: return 0.5
        tau = []
        for lag in lags:
            diffs = np.subtract(prices[lag:], prices[:-lag])
            tau.append(np.std(diffs))
        
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        return reg[0]

class TrendModule:
    def __init__(self):
        self.filters: Dict[str, KalmanTrendFilter] = {}
        
    def get_trend_state(self, symbol: str, price: float, history: List[float]) -> Dict[str, any]:
        if symbol not in self.filters:
            self.filters[symbol] = KalmanTrendFilter()
            
        kf_data = self.filters[symbol].update(price)
        hurst = HurstPersistence.calculate(history)
        
        # Regime logic
        regime = "CHOP"
        strength = abs(kf_data["velocity"])
        
        if hurst > 0.55:
            regime = "TRENDING" if strength > 0.0001 else "EQUILIBRIUM"
        elif hurst < 0.45:
            regime = "MEAN_REVERSION"
            
        return {
            "direction": 1 if kf_data["velocity"] > 0 else -1,
            "strength": strength,
            "acceleration": kf_data["acceleration"],
            "regime": regime,
            "hurst": hurst,
            "is_stable": hurst > 0.5 and abs(kf_data["acceleration"]) < strength * 0.1
        }
