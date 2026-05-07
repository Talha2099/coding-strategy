import numpy as np
from typing import List, Callable

class MonteCarloEngine:
    """
    Simulates price paths for probability estimation.
    """
    def __init__(self, n_paths: int = 10000):
        self.n_paths = n_paths

    def simulate(self, 
                 start_price: float, 
                 steps: int, 
                 dt: float, 
                 process_func: Callable[[np.ndarray, float], np.ndarray]) -> np.ndarray:
        """
        Broadcasting-optimized path simulation.
        """
        paths = np.zeros((self.n_paths, steps))
        paths[:, 0] = start_price
        
        for t in range(1, steps):
            paths[:, t] = process_func(paths[:, t-1], dt)
            
        return paths

class GeometricBrownianMotion:
    """
    Standard model for price paths: dS = mu*S*dt + sigma*S*dW
    """
    def __init__(self, mu: float, sigma: float):
        self.mu = mu
        self.sigma = sigma

    def next_step(self, s: np.ndarray, dt: float) -> np.ndarray:
        dw = np.random.normal(0, np.sqrt(dt), size=s.shape)
        return s * np.exp((self.mu - 0.5 * self.sigma**2) * dt + self.sigma * dw)

class OrnsteinUhlenbeck:
    """
    Mean-reverting process for spread/vol: dX = theta*(mu - X)dt + sigma*dW
    """
    def __init__(self, theta: float, mu: float, sigma: float):
        self.theta = theta
        self.mu = mu
        self.sigma = sigma

    def next_step(self, x: np.ndarray, dt: float) -> np.ndarray:
        dw = np.random.normal(0, np.sqrt(dt), size=x.shape)
        return x + self.theta * (self.mu - x) * dt + self.sigma * dw
