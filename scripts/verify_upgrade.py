from datetime import datetime
import numpy as np
from src.core.contracts.spec import ContractManager
from src.core.contracts.config_examples import GOLD_XAUUSD, AAPL_STOCK
from src.indicators.trend_filter import TrendModule
from src.risk.asset_aware_risk import MultiAssetRiskEngine, CrashProtectionModule

def verify_system():
    print("--- 1. Verification: Contract & Session Layer ---")
    cm = ContractManager()
    cm.register(GOLD_XAUUSD)
    cm.register(AAPL_STOCK)
    
    london_time = datetime(2024, 5, 20, 10, 0) # 10:00 UTC
    session = cm.get_session(london_time)
    print(f"Session at {london_time}: {session}")
    
    print("\n--- 2. Verification: Kalman Trend Filter ---")
    tm = TrendModule()
    # Simulate a trend: [100, 101, 102, 103...]
    prices = [100 + i + (np.random.normal() * 0.1) for i in range(50)]
    state = tm.get_trend_state("XAUUSD", prices[-1], prices)
    print(f"Trend Direction: {state['direction']}, Regime: {state['regime']}, Hurst: {state['hurst']:.2f}")

    print("\n--- 3. Verification: Asset-Aware Risk ---")
    risk = MultiAssetRiskEngine(cm.specs)
    # Check AAPL shorting
    valid, msg = risk.validate_trade("AAPL", -10, is_overnight=False, equity=100000.0)
    print(f"AAPL Short Validation: {valid} ({msg})")
    
    # Check Position Sizing for GOLD
    size = risk.get_position_sizing("XAUUSD", volatility=0.002, equity=100000.0, stop_dist=5.0)
    print(f"XAUUSD Position Size (1% Risk, 5pt Stop): {size} lots")

    print("\n--- 4. Verification: Crash Protection ---")
    crash = CrashProtectionModule()
    # High vol spike
    status = crash.should_block("XAUUSD", current_vol=0.015, correlations=np.eye(1))
    print(f"Volatility Shock Block: {status['block']} (Reason: {status.get('reason')})")

if __name__ == "__main__":
    verify_system()
