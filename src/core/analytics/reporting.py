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
    def compute_sortino(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        if len(returns) < 2: return 0.0
        avg_ret = returns.mean()
        downside_rets = returns[returns < 0]
        if len(downside_rets) < 2: return 0.0
        downside_std = downside_rets.std()
        if downside_std == 0: return 0.0
        return (avg_ret - risk_free_rate) / downside_std * np.sqrt(252)

    @staticmethod
    def generate_report(history: List[Dict], equity_curve: List[float]) -> Dict:
        trades = [h for h in history if h.get("type") == "EXIT"]
        if not trades: return {"error": "No trades found"}
        
        df = pd.DataFrame(trades)
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        
        # Helper for attribution
        def get_group_stats(group_df):
            win_rate = len(group_df[group_df["pnl"] > 0]) / len(group_df) if len(group_df) > 0 else 0
            gross_profits = group_df[group_df["pnl"] > 0]["pnl"].sum()
            gross_losses = abs(group_df[group_df["pnl"] < 0]["pnl"].sum())
            pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
            return {
                "trades": len(group_df),
                "win_rate": round(win_rate, 4),
                "profit_factor": round(pf, 2),
                "total_pnl": round(group_df["pnl"].sum(), 2)
            }

        # attribution
        strat_attribution = {name: get_group_stats(group) for name, group in df.groupby("strategy")}
        regime_attribution = {rt.name if hasattr(rt, "name") else str(rt): get_group_stats(group) for rt, group in df.groupby("regime")}
        session_attribution = {st.name if hasattr(st, "name") else str(st): get_group_stats(group) for st, group in df.groupby("session")}
        asset_attribution = {ac: get_group_stats(group) for ac, group in df.groupby("asset_class")}
        
        # Phase 8: Trend specific attribution
        trend_stage_attribution = {}
        if "trend_stage" in df.columns:
            trend_stage_attribution = {stage: get_group_stats(group) for stage, group in df.groupby("trend_stage")}
            
        # Costs and Decay
        total_slippage = df["slippage"].sum() if "slippage" in df.columns else 0.0
        
        return {
            "overall": {
                "total_trades": len(df),
                "equity_final": round(equity_curve[-1], 2),
                "max_drawdown": round(PerformanceReporter.compute_drawdown(equity_curve), 4),
                "sharpe": round(PerformanceReporter.compute_sharpe(returns), 2),
                "sortino": round(PerformanceReporter.compute_sortino(returns), 2),
                "return_pct": round((equity_curve[-1] / equity_curve[0] - 1) * 100, 2),
                "total_slippage_cost": round(total_slippage, 2)
            },
            "attribution": {
                "strategy": strat_attribution,
                "regime": regime_attribution,
                "session": session_attribution,
                "asset_class": asset_attribution,
                "trend_stage": trend_stage_attribution
            }
        }
