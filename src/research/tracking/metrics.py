import numpy as np
from typing import List, Dict

def calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    return (np.mean(returns) - risk_free_rate) / np.std(returns) * np.sqrt(252) # Annualized

def calculate_max_drawdown(equity_curve: np.ndarray) -> float:
    if len(equity_curve) == 0:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd

class PerformanceTracker:
    def __init__(self):
        self.equity_history = []
        self.trades_history = []

    def add_trade(self, trade_result: Dict):
        self.trades_history.append(trade_result)
        self.equity_history.append(trade_result.get("pnl", 0.0))

    def get_metrics(self) -> Dict[str, float]:
        returns = np.array(self.equity_history)
        return {
            "sharpe": calculate_sharpe(returns),
            "max_drawdown": calculate_max_drawdown(np.cumsum(returns) + 100000),
            "win_rate": len([r for r in returns if r > 0]) / len(returns) if len(returns) > 0 else 0
        }
