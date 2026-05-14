import numpy as np
from typing import List

class TrendPersistenceEngine:
    """
    PHASE 9: Advanced research modules for trend persistence and persistence estimation.
    Higher Hurst exponent (> 0.5) indicates trending behavior (persistence).
    Hurst < 0.5 indicates mean-reverting behavior (anti-persistence).
    """
    
    @staticmethod
    def compute_hurst(prices: List[float]) -> float:
        """
        Calculates the Hurst exponent using the R/S method.
        """
        if len(prices) < 32:
            return 0.5
            
        y = np.array(prices)
        lags = range(2, 20)
        
        # Calculate the variance of the differences with each lag
        tau = [np.sqrt(np.std(np.subtract(y[lag:], y[:-lag]))) for lag in lags]
        
        # Calculate the slope of the log plot -> Hurst exponent
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        
        # Correction for random walk: Hurst = slope * 2.0 (standard for variance-based lag)
        # But usually Hurst is slope. 0.5 is RW.
        hurst = poly[0]
        return float(hurst)

    @staticmethod
    def kalman_filter_price(prices: List[float]):
        """
        Basic Kalman filter for noise reduction and trend derivation.
        """
        if not prices:
            return 0.0
            
        z = np.array(prices)
        n_iter = len(z)
        sz = (n_iter,)
        
        Q = 1e-5 # process variance
        R = 0.01 # estimate of measurement variance, change to see effect
        
        xhat = np.zeros(sz)      # a posteri estimate of x
        P = np.zeros(sz)         # a posteri error estimate
        xhatminus = np.zeros(sz) # a priori estimate of x
        Pminus = np.zeros(sz)    # a priori error estimate
        K = np.zeros(sz)         # gain or blending factor
        
        xhat[0] = z[0]
        P[0] = 1.0
        
        for k in range(1, n_iter):
            # time update
            xhatminus[k] = xhat[k-1]
            Pminus[k] = P[k-1] + Q
            
            # measurement update
            K[k] = Pminus[k] / (Pminus[k] + R)
            xhat[k] = xhatminus[k] + K[k] * (z[k] - xhatminus[k])
            P[k] = (1 - K[k]) * Pminus[k]
            
        return xhat[-1]
