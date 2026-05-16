from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np
from src.core.types.trading import FillResult, Candle
from src.core.types.strategy import RegimeType, StrategyFamily
from src.core.contracts.instrument_spec import InstrumentSpec
from src.core.contracts.instrument_registry import InstrumentRegistry

class DriftMonitor:
    """
    PHASE 13: Monitoring and Drift Engine.
    Tracks if the market behavior is drifting away from the instrument's profile.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.spec = InstrumentRegistry.get_spec(symbol)
        
        # Historical stats for drift detection
        self.performance_history: List[Dict] = []
        self.slippage_history: List[float] = []
        self.spread_history: List[float] = []
        self.volatility_history: List[float] = []
        self.gap_history: List[float] = []
        self.behavior_score_history: Dict[str, List[float]] = {
            "trend_quality": [],
            "mean_reversion": [],
            "fake_breakout_prob": [],
            "volatility_intensity": []
        }
        
    def record_behavior_scores(self, scores: Dict[str, float]):
        for k, v in scores.items():
            if k in self.behavior_score_history:
                self.behavior_score_history[k].append(v)
                if len(self.behavior_score_history[k]) > 500:
                    self.behavior_score_history[k].pop(0)

        # Baseline expectations from Spec
        self.baseline_spread = self.spec.cost_model.spread_fixed
        self.baseline_slippage = self.spec.cost_model.slippage_base_bps

    def record_execution(self, fill: FillResult):
        self.slippage_history.append(fill.slippage)
        if len(self.slippage_history) > 100:
            self.slippage_history.pop(0)
            
    def record_market_state(self, spread: float, vol: float, gap: float = 0.0):
        self.spread_history.append(spread)
        self.volatility_history.append(vol)
        self.gap_history.append(gap)
        
        if len(self.spread_history) > 500:
            self.spread_history.pop(0)
            self.volatility_history.pop(0)
            self.gap_history.pop(0)

    def check_drift(self) -> Dict[str, Any]:
        """
        Calculates drift metrics compared to the instrument spec.
        """
        results = {
            "symbol": self.symbol,
            "timestamp": datetime.now().isoformat(),
            "drifts": {},
            "is_critical": False
        }
        
        if not self.spread_history:
            return results

        # 1. Cost Drift (Spread)
        avg_spread = float(np.mean(self.spread_history[-50:]))
        spread_drift = (avg_spread / self.baseline_spread) if self.baseline_spread > 0 else 1.0
        results["drifts"]["cost"] = spread_drift
        
        # 2. Execution Drift (Slippage)
        if self.slippage_history:
            # Convert avg slippage to bps of price (approximate)
            avg_slippage = float(np.mean(self.slippage_history[-20:]))
            # Just tracking relative change for now
            results["drifts"]["execution"] = avg_slippage
            
        # 3. Gap Behavior Shift
        if self.gap_history:
            avg_gap = float(np.mean(self.gap_history[-100:]))
            expected_gap = self.spec.behavior.gap_frequency
            gap_drift = (avg_gap / expected_gap) if expected_gap > 0 else 1.0
            results["drifts"]["gap"] = gap_drift

        # 4. Behavioral Drift Detection
        if self.behavior_score_history["trend_quality"]:
            avg_trend = np.mean(self.behavior_score_history["trend_quality"][-100:])
            # If current trend quality is much lower than expected trend persistence
            drift_trend = avg_trend / (self.spec.behavior.trend_persistence + 1e-9)
            results["drifts"]["trend_behavior"] = float(drift_trend)

        # 5. Critical Alerting
        if spread_drift > 3.0: # Spread tripled
             results["is_critical"] = True
             results["reason"] = "EXTREME_SPREAD_DRIFT"
             
        return results

class GlobalMonitoringEngine:
    _monitors: Dict[str, DriftMonitor] = {}
    
    @classmethod
    def get_monitor(cls, symbol: str) -> DriftMonitor:
        if symbol not in cls._monitors:
            cls._monitors[symbol] = DriftMonitor(symbol)
        return cls._monitors[symbol]
    
    @classmethod
    def run_daily_audit(cls) -> List[Dict]:
        audits = []
        for symbol, monitor in cls._monitors.items():
            audits.append(monitor.check_drift())
        return audits
