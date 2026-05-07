import numpy as np
from typing import List

class MicrostructureSDE:
    """
    Models bid-ask spreads and liquidity as mean-reverting processes.
    OU Process: dS_t = theta * (mu - S_t)dt + sigma * dW_t
    """
    def __init__(self, theta: float, mu: float, sigma: float):
        self.theta = theta
        self.mu = mu
        self.sigma = sigma

    def simulate_path(self, s0: float, dt: float, steps: int) -> np.ndarray:
        path = np.zeros(steps)
        path[0] = s0
        for t in range(1, steps):
            dw = np.random.normal(0, np.sqrt(dt))
            path[t] = path[t-1] + self.theta * (self.mu - path[t-1]) * dt + self.sigma * dw
        return path

class GirsanovTransform:
    """
    Measure changes for risk-neutral pricing and entry optimization.
    """
    @staticmethod
    def drift_shift(drift: float, volatility: float, market_price_of_risk: float) -> float:
        return drift - (market_price_of_risk * volatility)

class MilsteinScheme:
    """
    Higher-order SDE discretization for complex microstructure models.
    """
    @staticmethod
    def step(x: float, dt: float, dw: float, drift_func, vol_func, vol_prime_func) -> float:
        f = drift_func(x)
        g = vol_func(x)
        g_p = vol_prime_func(x)
        
        # Milstein correction term: 0.5 * g * g' * (dw^2 - dt)
        return x + f * dt + g * dw + 0.5 * g * g_p * (dw**2 - dt)
