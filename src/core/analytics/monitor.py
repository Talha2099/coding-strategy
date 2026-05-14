import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from src.core.types.strategy import StrategyStats, StrategyFamily

class StrategyMonitor:
    """
    Monitors alpha decay, regime drift, and signal quality over time.
    Provides early warning for strategy failure.
    """
    def __init__(self, window: int = 200):
        self.window = window
        self.trade_history: List[Dict] = []
        self.regime_history: List[str] = []
        
    def add_trade_record(self, record: Dict):
        """Adds a completed trade record for monitoring."""
        self.trade_history.append(record)
        if len(self.trade_history) > self.window:
            self.trade_history.pop(0)
            
    def add_regime_record(self, regime: str):
        self.regime_history.append(regime)
        if len(self.regime_history) > self.window:
            self.regime_history.pop(0)

    def assess_alpha_decay(self, strategy_name: str) -> Dict[str, float]:
        """
        Detects if a strategy's win rate, RR, or execution quality is trending down.
        """
        strat_trades = [t for t in self.trade_history if t.get('strategy') == strategy_name]
        if len(strat_trades) < 20:
             return {"decay_risk": 0.0}
             
        df = pd.DataFrame(strat_trades)
        df['win'] = (df['pnl'] > 0).astype(int)
        
        # Compare first half vs second half
        mid = len(df) // 2
        wr1 = df['win'].iloc[:mid].mean()
        wr2 = df['win'].iloc[mid:].mean()
        
        pf1 = df[df['pnl'] > 0]['pnl'].iloc[:mid].sum() / abs(df[df['pnl'] < 0]['pnl'].iloc[:mid].sum() + 1e-9)
        pf2 = df[df['pnl'] > 0]['pnl'].iloc[mid:].sum() / abs(df[df['pnl'] < 0]['pnl'].iloc[mid:].sum() + 1e-9)
        
        slippage_avg1 = df['slippage'].iloc[:mid].mean() if 'slippage' in df.columns else 0.0
        slippage_avg2 = df['slippage'].iloc[mid:].mean() if 'slippage' in df.columns else 0.0

        wr_decay = (wr1 - wr2) / (wr1 + 1e-9)
        pf_decay = (pf1 - pf2) / (pf1 + 1e-9)
        slippage_drift = (slippage_avg2 - slippage_avg1) / (slippage_avg1 + 1e-9) if slippage_avg1 > 0 else 0.0
        
        return {
            "wr_decay": float(wr_decay),
            "pf_decay": float(pf_decay),
            "slippage_drift": float(slippage_drift),
            "decay_risk": float(max(0, (wr_decay + pf_decay + slippage_drift) / 3))
        }

    def assess_scenario_mismatch(self) -> Dict[str, float]:
        """Detects if certain regimes or failure reasons are becoming more frequent."""
        if not self.trade_history: return {}
        df = pd.DataFrame(self.trade_history)
        
        results = {}
        if 'regime' in df.columns:
            df['win'] = (df['pnl'] > 0).astype(int)
            regime_stats = df.groupby('regime')['win'].mean().to_dict()
            results["hit_rate_by_regime"] = {str(k): float(v) for k, v in regime_stats.items()}
            
        if 'reason' in df.columns:
            reasons = df['reason'].value_counts(normalize=True).to_dict()
            results["failure_reasons"] = {str(k): float(v) for k, v in reasons.items()}
            
        return results

    def detect_regime_drift(self) -> float:
        """
        Measures if the current distribution of regimes is shifting significantly.
        """
        if len(self.regime_history) < 100: return 0.0
        
        mid = len(self.regime_history) // 2
        h1 = pd.Series(self.regime_history[:mid]).value_counts(normalize=True)
        h2 = pd.Series(self.regime_history[mid:]).value_counts(normalize=True)
        
        # Distance between probability distributions
        all_regimes = set(h1.index) | set(h2.index)
        dist = 0.0
        for r in all_regimes:
            dist += abs(h1.get(r, 0) - h2.get(r, 0))
            
        return float(dist / 2.0)

    def get_health_report(self) -> Dict:
        """Aggregates all monitoring metrics."""
        strat_names = set(t.get('strategy') for t in self.trade_history)
        decay_reports = {name: self.assess_alpha_decay(name) for name in strat_names}
        
        return {
            "strategy_decay": decay_reports,
            "regime_drift": self.detect_regime_drift(),
            "scenario_mismatch": self.assess_scenario_mismatch(),
            "timestamp": datetime.now()
        }
