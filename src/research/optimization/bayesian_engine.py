import numpy as np
import pandas as pd
from typing import Dict, Any, Callable, List
import logging

try:
    import optuna
except ImportError:
    optuna = None

class BayesianOptimizationEngine:
    """
    Dedicated engine for hyperparameter optimization using Bayesian techniques (TPE).
    Capable of optimizing strategies, risk parameters, and regime detection.
    """
    def __init__(self, n_trials: int = 50, metric: str = "sharpe"):
        self.n_trials = n_trials
        self.metric = metric
        self.logger = logging.getLogger("Optimizer")
        
        if optuna is None:
            self.logger.warning("Optuna not installed. Please install 'optuna' for Bayesian optimization. Falling back to dummy mode.")

    def optimize(self, 
                 objective_func: Callable[[Dict[str, Any]], float], 
                 param_space: Dict[str, Any],
                 direction: str = "maximize"):
        """
        Runs the optimization loop.
        
        param_space example:
        {
            "donchian_window": {"type": "int", "low": 10, "high": 50},
            "risk_percent": {"type": "float", "low": 0.005, "high": 0.05},
            "regime_threshold": {"type": "categorical", "choices": [0.5, 0.6, 0.7]}
        }
        """
        if optuna is None:
            return self._fallback_random_search(objective_func, param_space, direction)

        study = optuna.create_study(direction=direction)
        
        def wrapper_objective(trial):
            params = {}
            for name, config in param_space.items():
                if config["type"] == "int":
                    params[name] = trial.suggest_int(name, config["low"], config["high"])
                elif config["type"] == "float":
                    params[name] = trial.suggest_float(name, config["low"], config["high"])
                elif config["type"] == "categorical":
                    params[name] = trial.suggest_categorical(name, config["choices"])
            
            return objective_func(params)

        study.optimize(wrapper_objective, n_trials=self.n_trials)
        
        return {
            "best_params": study.best_params,
            "best_value": study.best_value,
            "all_trials": study.trials_dataframe()
        }

    def _fallback_random_search(self, func, space, direction):
        """Minimal fallback if optuna is missing."""
        best_val = -float('inf') if direction == "maximize" else float('inf')
        best_params = None
        
        for _ in range(self.n_trials):
            params = {}
            for name, config in space.items():
                if config["type"] == "int":
                    params[name] = np.random.randint(config["low"], config["high"] + 1)
                elif config["type"] == "float":
                    params[name] = np.random.uniform(config["low"], config["high"])
                elif config["type"] == "categorical":
                    params[name] = np.random.choice(config["choices"])
            
            val = func(params)
            if direction == "maximize":
                if val > best_val:
                    best_val = val
                    best_params = params
            else:
                if val < best_val:
                    best_val = val
                    best_params = params
                    
        return {"best_params": best_params, "best_value": best_val}

class TuningObjectiveFactory:
    """
    Helps build search spaces and objectives for different system components.
    """
    @staticmethod
    def get_strategy_space(strategy_name: str) -> Dict[str, Any]:
        spaces = {
            "DonchianBreakout": {
                "window": {"type": "int", "low": 10, "high": 100}
            },
            "BollingerMR": {
                "window": {"type": "int", "low": 10, "high": 50},
                "num_std": {"type": "float", "low": 1.5, "high": 3.0}
            },
            "VWAPPullback": {
                "pullback_threshold": {"type": "float", "low": 0.001, "high": 0.01}
            }
        }
        return spaces.get(strategy_name, {})

    @staticmethod
    def get_risk_space() -> Dict[str, Any]:
        return {
            "risk_per_trade": {"type": "float", "low": 0.001, "high": 0.03},
            "max_exposure": {"type": "float", "low": 0.1, "high": 1.0}
        }
