from datetime import datetime, timedelta
from src.core.types.trading import Tick
from src.backtest.engine.simulator import EventDrivenBacktester
from src.core.contracts.spec import ContractManager, InstrumentSpec, AssetClass, SessionType
from src.risk.asset_aware_risk import MultiAssetRiskEngine, CrashProtectionModule
from src.execution.engine.base import ExecutionEngine
from src.regime.engine import RegimeEngine
from src.strategies.registry import StrategyRouter
from src.strategies.breakout.donchian import DonchianBreakout
from src.strategies.breakout.orb import OpeningRangeBreakout
from src.strategies.breakout.volatility_compression import VolatilityCompressionBreakout
from src.strategies.pullback.vwap_pullback import VWAPPullback
from src.strategies.pullback.ema_pullback import EMAPullback
from src.strategies.mean_reversion.bollinger_mr import BollingerMeanReversion
from src.strategies.mean_reversion.zscore_mr import ZScoreMeanReversion
from src.strategies.gap.gap_and_go import GapAndGo
from src.strategies.gap.gap_fill import GapFill
from src.strategies.range.range_fade import RangeFade

def run_verification():
    # 1. Setup Environment
    gold_spec = InstrumentSpec(
        symbol="XAUUSD",
        asset_class=AssetClass.CFD,
        contract_size=100,
        point_value=1.0,
        min_lot=0.01,
        lot_step=0.01,
        swap_long=-5.0,
        swap_short=-2.0,
        allow_short=True,
        allow_overnight=True
    )
    
    cm = ContractManager()
    cm.add_spec(gold_spec)
    
    risk = MultiAssetRiskEngine({"XAUUSD": gold_spec})
    exec_eng = ExecutionEngine()
    regime_eng = RegimeEngine()
    router = StrategyRouter()
    crash = CrashProtectionModule()
    
    # Register Strategies
    router.register_strategy(DonchianBreakout(gold_spec))
    router.register_strategy(OpeningRangeBreakout(gold_spec))
    router.register_strategy(VWAPPullback(gold_spec))
    router.register_strategy(EMAPullback(gold_spec))
    router.register_strategy(BollingerMeanReversion(gold_spec))
    router.register_strategy(ZScoreMeanReversion(gold_spec))
    router.register_strategy(GapAndGo(gold_spec))
    router.register_strategy(GapFill(gold_spec))
    router.register_strategy(RangeFade(gold_spec))
    router.register_strategy(VolatilityCompressionBreakout(gold_spec))
    
    bt = EventDrivenBacktester(
        contract_manager=cm,
        risk_engine=risk,
        exec_engine=exec_eng,
        regime_engine=regime_eng,
        strategy_router=router,
        crash_module=crash
    )
    
    # 2. Mock some data (Trend followed by Mean Reversion)
    ticks = []
    base_price = 2000.0
    now = datetime(2024, 1, 1, 9, 0)
    
    # 1. Trend High Volatility
    for i in range(200):
        base_price += 1.0
        ticks.append(Tick(ts=now + timedelta(minutes=i), price=base_price, size=1.0, side="buy", symbol="XAUUSD"))
        
    # 2. Ranging Low Volatility
    for i in range(200, 500):
        price = base_price + (2.0 if i % 2 == 0 else -2.0)
        ticks.append(Tick(ts=now + timedelta(minutes=i), price=price, size=1.0, side="buy", symbol="XAUUSD"))
        
    # 3. Breakout Volatility Expansion
    for i in range(500, 600):
        base_price += (i - 500) * 0.1
        ticks.append(Tick(ts=now + timedelta(minutes=i), price=base_price, size=1.0, side="buy", symbol="XAUUSD"))

    # 3. Run Backtest
    print("Running multi-strategy technical backtest...")
    summary = bt.run(ticks)
    
    report = summary["report"]
    overall = report["overall"]
    print(f"Final Equity: {overall['equity_final']:.2f}")
    print(f"Total Trades: {overall['total_trades']}")
    print(f"Return: {overall['return_pct']}%")
    print(f"Max DD: {overall['max_drawdown']:.4f}")
    print("\nStrategy Attribution:")
    for strat, stats in report['attribution'].items():
        print(f" - {strat}: Trades={stats['trades']}, WinRate={stats['win_rate']}, PF={stats['profit_factor']}, PnL={stats['total_pnl']}")

if __name__ == "__main__":
    run_verification()
