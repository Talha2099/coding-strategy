import pytest
import numpy as np
from src.core.math_engine.linear_algebra import PCAReducer, OLSRegression
from src.core.math_engine.markov_bayesian import HiddenMarkovModel
from src.core.math_engine.finance_models import MertonJumpDiffusion, KellyCriterion
from src.core.math_engine.time_series import GARCH11, FourierCycleDetector

def test_pca_reducer():
    data = np.random.rand(100, 10)
    # Make some columns redundant
    data[:, 5:] = data[:, :5] * 2
    
    pca = PCAReducer(variance_threshold=0.99)
    pca.fit(data)
    transformed = pca.transform(data)
    
    # Should have fewer than 10 components
    assert transformed.shape[1] < 10

def test_ols_regression():
    X = np.array([[1], [2], [3], [4]])
    y = np.array([2, 4, 6, 8])
    
    ols = OLSRegression()
    ols.fit(X, y)
    pred = ols.predict(np.array([[5]]))
    
    assert round(float(pred[0]), 2) == 10.0

def test_hmm_decoding():
    hmm = HiddenMarkovModel(n_states=2)
    # Force some parameters for testing
    hmm.transition_matrix = np.array([[0.9, 0.1], [0.1, 0.9]])
    hmm.emission_params = [{"mean": 10, "std": 1}, {"mean": -10, "std": 1}]
    
    obs = np.array([10, 11, 9, -10, -11, -9])
    states = hmm.decode(obs)
    
    assert states[0] == 0
    assert states[3] == 1

def test_merton_jump_diffusion():
    path = MertonJumpDiffusion.simulate_path(S0=100, T=1, mu=0.05, sigma=0.2, lambda_j=1, mu_j=0, sigma_j=0.1)
    assert len(path) == 101
    assert path[0] == 100

def test_kelly_criterion():
    fraction = KellyCriterion.calculate_fraction(win_prob=0.6, rr=2.0)
    # f* = (0.6*3 - 1)/2 = 0.8/2 = 0.4. Capped at 0.2
    assert fraction == 0.2
    
    low_prob = KellyCriterion.calculate_fraction(win_prob=0.3, rr=2.0)
    # f* = (0.3*3 - 1)/2 = -0.1/2 = -0.05 -> 0.0
    assert low_prob == 0.0

def test_garch_forecast():
    garch = GARCH11(omega=0.01, alpha=0.1, beta=0.8)
    vol1 = garch.forecast(0.0) # Should be sqrt(0.01 + 0.8*1^2) = sqrt(0.81) = 0.9
    assert round(vol1, 2) == 0.9

def test_fourier_cycle():
    t = np.linspace(0, 1, 100)
    data = np.sin(2 * np.pi * 5 * t) + np.sin(2 * np.pi * 10 * t)
    cycles = FourierCycleDetector.detect_cycles(data, top_k=2)
    
    # Cycles are frequencies: 5 and 10
    # ffxfreq returns cycles per step
    assert len(cycles) == 2
