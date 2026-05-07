import numpy as np
from typing import List, Tuple

class FourierCycleDetector:
    """
    Extracts dominant session-cycle frequencies from returns.
    """
    @staticmethod
    def detect_cycles(data: np.ndarray, top_k: int = 3) -> List[float]:
        fft_values = np.fft.fft(data)
        frequencies = np.fft.fftfreq(len(data))
        
        # Power spectrum
        power = np.abs(fft_values)**2
        indices = np.argsort(power[frequencies > 0])[::-1]
        
        return frequencies[frequencies > 0][indices[:top_k]].tolist()

class GARCH11:
    """
    Intra-session volatility forecasting: sigma^2_t = omega + alpha*r^2_{t-1} + beta*sigma^2_{t-1}
    """
    def __init__(self, omega: float, alpha: float, beta: float):
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.last_vol = 1.0 # Initial guess

    def forecast(self, last_return: float) -> float:
        next_vol_sq = self.omega + self.alpha * (last_return**2) + self.beta * (self.last_vol**2)
        self.last_vol = np.sqrt(next_vol_sq)
        return self.last_vol

class ARIMA:
    """
    Rolling forecasts for price movements (p,d,q simplified).
    """
    def __init__(self, ar_coeffs: np.ndarray, ma_coeffs: np.ndarray):
        self.ar = ar_coeffs
        self.ma = ma_coeffs

    def predict(self, history: np.ndarray, errors: np.ndarray) -> float:
        # AR part
        ar_val = np.sum(history[-len(self.ar):][::-1] * self.ar)
        # MA part
        ma_val = np.sum(errors[-len(self.ma):][::-1] * self.ma)
        return ar_val + ma_val
