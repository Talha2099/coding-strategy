import numpy as np
from scipy.stats import norm
from typing import Dict

class MertonJumpDiffusion:
    """
    State-of-the-art model for CFD/Spot price dynamics with jump risk.
    Captures price discontinuities (gaps) that Black-Scholes ignores.
    """
    @staticmethod
    def simulate_path(S0: float, T: float, mu: float, sigma: float, 
                      lambda_j: float, mu_j: float, sigma_j: float, 
                      steps: int = 100) -> np.ndarray:
        """
        mu: drift
        sigma: volatility
        lambda_j: jump intensity (jumps per year)
        mu_j: mean jump size (log-normal)
        sigma_j: jump volatility
        """
        dt = T / steps
        paths = np.zeros(steps + 1)
        paths[0] = S0
        
        for t in range(1, steps + 1):
            # Diffusion part
            z_d = np.random.normal(0, 1)
            # Jump part (Poisson process)
            n_jumps = np.random.poisson(lambda_j * dt)
            jump_component = 0
            if n_jumps > 0:
                jump_component = np.sum(np.random.normal(mu_j, sigma_j, n_jumps))
            
            # Stochastic Differential Equation step
            paths[t] = paths[t-1] * np.exp(
                (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z_d + jump_component
            )
        return paths

class KellyCriterion:
    """
    Optimal position sizing for CFD accounts to maximize long-term growth (Log-wealth).
    """
    @staticmethod
    def calculate_fraction(win_prob: float, rr: float, fraction_cap: float = 0.2) -> float:
        """
        win_prob: estimated probability of trade success (from MetaModel)
        rr: reward-to-risk ratio
        fraction_cap: safety cap (e.g. 20% max leverage)
        """
        if rr <= 0 or win_prob <= 0: return 0.0
        # f* = (p(b+1) - 1) / b  where b is odds (rr)
        k_fraction = (win_prob * (rr + 1) - 1) / rr
        
        # We usually use "Half-Kelly" or "Fractional Kelly" for risk management
        return max(0.0, min(k_fraction, fraction_cap))

class TechnicalFamaFrench:
    """
    Factor model for return attribution.
    """
    def __init__(self):
        self.betas = None # [Momentum, Vol, Volume, Session]

    def estimate_factors(self, returns: np.ndarray, factors: np.ndarray):
        # factors: columns of [Mom, Vol, Volm, Sess]
        from .linear_algebra import OLSRegression
        model = OLSRegression()
        model.fit(factors, returns)
        self.betas = model.beta
        return self

class ExpectancyCalculator:
    """
    Determines 'Risk-Neutral Edge' at SMC levels.
    """
    @staticmethod
    def calculate(win_prob: float, rr: float, commission: float = 0.0001) -> float:
        # Edge = (P(W) * R) - (P(L) * 1) - costs
        return (win_prob * rr) - (1 - win_prob) - commission
