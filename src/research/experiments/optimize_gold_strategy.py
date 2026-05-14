import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from src.core.types.trading import Tick
from src.backtest.engine.simulator import EventDrivenBacktester
from src.core.contracts.spec import ContractManager, InstrumentSpec, AssetClass
from src.risk.asset_aware_risk import MultiAssetRiskEngine, CrashProtectionModule
from src.execution.engine.base import ExecutionEngine
from src.regime.engine import RegimeEngine
from src.regime.mtf_engine import MTFRegimeEngine
from src.strategies.registry import StrategyRouter
from src.strategies.breakout.donchian import DonchianBreakout
from src.research.optimization.bayesian_engine import BayesianOptimizationEngine, TuningObjectiveFactory

def generate_mock_ticks(n_minutes: int = 1000):
    ticks = []
    base_price = 2000.0
    now = datetime(2024, 1, 1, 9, 0)
    for i in range(n_minutes):
        # Trending/Ranging mixed
        if i < 300: base_price += 0.5 # Trend
        elif i < 700: base_price += (1.0 if i % 2 == 0 else -1.0) # Range
        else: base_price += 1.2 # Stronger breakout
        ticks.append(Tick(ts=now + timedelta(minutes=i), price=base_price, size=1.0, side="buy", symbol="XAUUSD"))
    return ticks

def objective(params: Dict[str, Any]):
    """
    Objective function for Bayesian optimizer.
    """
    # 1. Setup Environment with Trial Parameters
    gold_spec = InstrumentSpec(
        symbol="XAUUSD",
        asset_class=AssetClass.CFD,
        contract_size=100,
        point_value=1.0,
        min_lot=0.01,
        lot_step=0.01
    )
    
    cm = ContractManager()
    cm.add_spec(gold_spec)
    
    # PARAMETER 1: Risk per trade
    risk = MultiAssetRiskEngine({"XAUUSD": gold_spec}, risk_per_trade=params.get("risk_per_trade", 0.01))
    
    exec_eng = ExecutionEngine()
    regime_eng = RegimeEngine()
    mtf_eng = MTFRegimeEngine()
    router = StrategyRouter(cm)
    crash = CrashProtectionModule()
    
    # PARAMETER 2: Strategy Hyperparameter
    router.register_strategy(DonchianBreakout(gold_spec, window=params.get("donchian_window", 20)))
    
    bt = EventDrivenBacktester(
        contract_manager=cm,
        risk_engine=risk,
        exec_engine=exec_eng,
        regime_engine=regime_eng,
        mtf_engine=mtf_eng,
        strategy_router=router,
        crash_module=crash
    )
    
    ticks = generate_mock_ticks(1000)
    summary = bt.run(ticks)
    
    # Extract Metric
    report = summary["report"]
    if "error" in report: return -100.0
    
    # For optimization, we can use Profit Factor or Net PnL or custom score
    pnl = report["overall"]["equity_final"] - 100000.0
    pf = report["attribution"].get("DonchianBreakout", {}).get("profit_factor", 0.0)
    
    # Return a composite score (e.g., PnL * PF)
    return pnl * (min(pf, 5.0))

def run_optimization():
    print("Initiating Bayesian Hyperparameter Optimization Engine...")
    
    engine = BayesianOptimizationEngine(n_trials=20)
    
    # Define Search Space
    space = {
        "donchian_window": {"type": "int", "low": 10, "high": 50},
        "risk_per_trade": {"type": "float", "low": 0.005, "high": 0.03}
    }
    
    print("Searching for optimal (Donchian Window, Risk Fraction) pairing...")
    results = engine.optimize(objective, space, direction="maximize")
    
    print("\n" + "="*40)
    print("Optimization Complete")
    print(f"Best Value: {results['best_value']:.2f}")
    print(f"Optimal Parameters: {results['best_params']}")
    print("="*40)

if __name__ == "__main__":
    run_optimization()
