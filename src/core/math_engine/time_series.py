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

class HurstExponent:
    """
    Calculates the Hurst Exponent to determine if a time series is:
    H < 0.5: Mean Reverting (Anti-persistent)
    H = 0.5: Random Walk (Brownian Motion)
    H > 0.5: Trending (Persistent)
    """
    @staticmethod
    def calculate(ts: np.ndarray, min_window: int = 8) -> float:
        """
        Simplified Rescaled Range (R/S) analysis.
        """
        if len(ts) < min_window * 2: return 0.5
        
        # Log returns
        lts = np.log(ts[1:] / ts[:-1])
        N = len(lts)
        
        # Calculate multiple window sizes
        max_k = int(np.floor(np.log2(N)))
        R_S_dict = []
        
        for k in range(min_window, N // 2, 8):
            # Divide into chunks of size k
            n_chunks = N // k
            rs_values = []
            for i in range(n_chunks):
                chunk = lts[i*k : (i+1)*k]
                # Mean centered
                mean_centered = chunk - np.mean(chunk)
                # Cumulative sum
                cum_sum = np.cumsum(mean_centered)
                # Range
                R = np.max(cum_sum) - np.min(cum_sum)
                # Std
                S = np.std(chunk)
                if S > 0:
                    rs_values.append(R / S)
            
            if rs_values:
                R_S_dict.append((np.log(k), np.log(np.mean(rs_values))))
        
        if len(R_S_dict) < 2: return 0.5
        
        # Fit line to log(k) and log(R/S)
        x = np.array([pt[0] for pt in R_S_dict])
        y = np.array([pt[1] for pt in R_S_dict])
        
        # Simple slope calculation
        H = np.polyfit(x, y, 1)[0]
        return float(H)
