import numpy as np

def calculate_volatility(prices: list[float], window: int = 14) -> float:
    if len(prices) < 2:
        return 0.0
    returns = np.diff(np.log(prices))
    return float(np.std(returns))

def normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)
