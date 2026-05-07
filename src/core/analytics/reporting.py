import pandas as pd
import numpy as np
from typing import List, Dict
from src.core.types.strategy import StrategyStats, StrategyFamily

class PerformanceReporter:
    """
    Computes advanced performance metrics for strategy groups.
    """
    @staticmethod
    def compute_sharpe(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        if len(returns) < 2: return 0.0
        avg_ret = returns.mean()
        std_ret = returns.std()
        if std_ret == 0: return 0.0
        return (avg_ret - risk_free_rate) / std_ret * np.sqrt(252) # Annualized approx

    @staticmethod
    def compute_drawdown(equity_curve: List[float]) -> float:
        if not equity_curve: return 0.0
        s = pd.Series(equity_curve)
        rolling_max = s.cummax()
        drawdowns = (s - rolling_max) / rolling_max
        return float(drawdowns.min())

    @staticmethod
    def generate_report(history: List[Dict], equity_curve: List[float]) -> Dict:
        trades = [h for h in history if h.get("type") == "EXIT"]
        if not trades: return {"error": "No trades found"}
        
        df = pd.DataFrame(trades)
        
        # Attribution by Strategy
        attribution = {}
        for (strategy_name), group in df.groupby("strategy"):
            win_rate = len(group[group["pnl"] > 0]) / len(group)
            gross_profits = group[group["pnl"] > 0]["pnl"].sum()
            gross_losses = abs(group[group["pnl"] < 0]["pnl"].sum())
            pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
            
            attribution[strategy_name] = {
                "trades": len(group),
                "win_rate": round(win_rate, 4),
                "profit_factor": round(pf, 2),
                "total_pnl": round(group["pnl"].sum(), 2),
                "avg_pnl": round(group["pnl"].mean(), 2)
            }
            
        return {
            "overall": {
                "total_trades": len(df),
                "equity_final": round(equity_curve[-1], 2),
                "max_drawdown": round(PerformanceReporter.compute_drawdown(equity_curve), 4),
                "return_pct": round((equity_curve[-1] / equity_curve[0] - 1) * 100, 2)
            },
            "attribution": attribution
        }
