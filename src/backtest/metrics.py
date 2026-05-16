import numpy as np
import pandas as pd
from typing import Dict, Any, List

class BacktestMetrics:
    """
    Calculates performance metrics for backtests.
    """
    
    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float = 100000.0) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "net_pnl": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
            
        df = pd.DataFrame(trades)
        
        # Basic calculations
        net_pnl = df['pnl'].sum()
        winners = df[df['pnl'] > 0]
        losers = df[df['pnl'] <= 0]
        
        win_rate = len(winners) / len(df) if len(df) > 0 else 0.0
        
        gross_profit = winners['pnl'].sum()
        gross_loss = abs(losers['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Equity curve for drawdown and Sharpe
        equity = [initial_capital]
        for p in df['pnl']:
            equity.append(equity[-1] + p)
        
        equity_series = pd.Series(equity)
        
        # Max Drawdown
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio (Daily proxy)
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
        
        return {
            "total_trades": len(df),
            "net_pnl": float(net_pnl),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "final_equity": float(equity[-1])
        }
