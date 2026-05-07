import numpy as np
from typing import List, Tuple

class HiddenMarkovModel:
    """
    4-state HMM for Market Regime detection.
    States: 0: Trending Up, 1: Trending Down, 2: Ranging, 3: High Vol/Toxic
    """
    def __init__(self, n_states: int = 4):
        self.n_states = n_states
        self.transition_matrix = np.full((n_states, n_states), 1.0/n_states)
        self.emission_params = [{"mean": 0, "std": 1} for _ in range(n_states)]
        self.pi = np.full(n_states, 1.0/n_states)

    def decode(self, observations: np.ndarray) -> np.ndarray:
        """
        Viterbi algorithm to find most likely state sequence.
        """
        T = len(observations)
        viterbi = np.zeros((T, self.n_states))
        backpointer = np.zeros((T, self.n_states), dtype=int)
        
        # Init
        for s in range(self.n_states):
            viterbi[0, s] = self.pi[s] * self._emission_prob(observations[0], s)
            
        # Induction
        for t in range(1, T):
            for s in range(self.n_states):
                probs = viterbi[t-1, :] * self.transition_matrix[:, s] * self._emission_prob(observations[t], s)
                viterbi[t, s] = np.max(probs)
                backpointer[t, s] = np.argmax(probs)
                
        # Path reconstruction
        path = np.zeros(T, dtype=int)
        path[-1] = np.argmax(viterbi[-1, :])
        for t in range(T-2, -1, -1):
            path[t] = backpointer[t+1, path[t+1]]
            
        return path

    def _emission_prob(self, x: float, state: int) -> float:
        p = self.emission_params[state]
        return (1.0 / (np.sqrt(2*np.pi) * p["std"])) * np.exp(-0.5 * ((x - p["mean"]) / p["std"])**2)

class BayesianUpdater:
    """
    Iterative posterior updates for regime probabilities.
    """
    def __init__(self, prior: np.ndarray = None):
        self.prior = prior if prior is not None else np.array([0.25, 0.25, 0.25, 0.25])
        self.alpha = np.ones(len(self.prior)) # Dirichlet

    def update(self, observed_state: int):
        self.alpha[observed_state] += 1
        # Posterior mean
        self.prior = self.alpha / np.sum(self.alpha)
        return self.prior

class DiscreteMarkovChain:
    """
    Predicts next state transitions (e.g. Range -> Trend).
    """
    def predict_next(self, current_state: int, transition_matrix: np.ndarray) -> int:
        return np.argmax(transition_matrix[current_state, :])
