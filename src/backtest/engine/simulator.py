import numpy as np
import uuid
from typing import List, Dict
from datetime import datetime
from src.core.types.trading import (
    Candle, Tick, OrderBookSnapshot, 
    TradeCandidate, ScoredTrade, ExecutionOrder, FillResult, Position
)
from src.market_microstructure.engine import MicrostructureEngine
from src.features.fusion.engine import FeatureFusionEngine
from src.ml.meta_labeling.model import MetaModel
from src.risk.asset_aware_risk import MultiAssetRiskEngine, CrashProtectionModule
from src.execution.engine.base import ExecutionEngine
from src.core.contracts.spec import ContractManager, SessionType
from src.indicators.trend_filter import TrendModule
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.regime.engine import RegimeEngine
from src.strategies.registry import StrategyRouter
from src.core.analytics.reporting import PerformanceReporter

class EventDrivenBacktester:
    def __init__(self, 
                 contract_manager: ContractManager,
                 risk_engine: MultiAssetRiskEngine,
                 exec_engine: ExecutionEngine,
                 regime_engine: RegimeEngine,
                 strategy_router: StrategyRouter,
                 crash_module: CrashProtectionModule):
        self.contract_manager = contract_manager
        self.risk_engine = risk_engine
        self.exec_engine = exec_engine
        self.regime_engine = regime_engine
        self.strategy_router = strategy_router
        self.crash_module = crash_module
        
        self.history = []
        self.equity_curve = [100000.0]
        self.current_positions: Dict[str, float] = {} # Summary for financing
        self.open_positions: List[Position] = [] # Granular tracking
        self.price_history: Dict[str, List[float]] = {}
        self.candle_history: Dict[str, List[Candle]] = {}
        self.last_ts: Dict[str, datetime] = {}
        
        # Strategy Tracking
        self.strategy_pnl: Dict[str, float] = {} # Strategy Name -> PnL
        self.family_pnl: Dict[StrategyFamily, float] = {sf: 0.0 for sf in StrategyFamily}
        
        self.pnl_stats = {
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "commissions": 0.0,
            "financing_costs": 0.0,
            "slippage_total": 0.0,
            "dividend_gains": 0.0
        }

    def on_tick(self, tick: Tick):
        symbol = tick.symbol
        if symbol not in self.price_history: 
            self.price_history[symbol] = []
            self.candle_history[symbol] = []
            self.last_ts[symbol] = tick.ts
        
        # 0. Gap Detection
        time_diff = (tick.ts - self.last_ts[symbol]).total_seconds()
        if time_diff > 3600 * 24: # More than a day
            self._handle_gap(symbol, tick.price, tick.ts)
        self.last_ts[symbol] = tick.ts

        self.price_history[symbol].append(tick.price)
        if len(self.price_history[symbol]) > 100: self.price_history[symbol].pop(0)
        
        # 0.1 Update Candles (Simplified: 1 minute candles)
        self._update_candles(tick)
        
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(tick.ts)
        
        # 1. Check Exits
        self._check_exits(tick)

        # 2. Regime Analysis
        regime = self.regime_engine.classify(self.candle_history[symbol]) if len(self.candle_history[symbol]) >= 20 else RegimeType.VOLATILE_UNSTABLE
        
        # 3. Strategy Scan
        ideas = self.strategy_router.get_trade_ideas(symbol, self.candle_history[symbol], regime)
        for idea in ideas:
            self.process_trade_idea(idea, tick.ts)
        
        # 4. Financing & Corporate Actions Check (at 22:00 UTC)
        if tick.ts.hour == 22 and tick.ts.minute == 0:
            self._apply_financing(symbol, tick.ts)
            self._apply_corporate_actions(symbol, tick.ts)

        self.history.append({
            "ts": tick.ts,
            "session": session,
            "regime": regime,
            "price": tick.price
        })

    def _update_candles(self, tick: Tick):
        """Builds 1-min candles from ticks."""
        symbol = tick.symbol
        ts_minute = tick.ts.replace(second=0, microsecond=0)
        
        if not self.candle_history[symbol] or self.candle_history[symbol][-1].ts != ts_minute:
            new_candle = Candle(ts=ts_minute, open=tick.price, high=tick.price, low=tick.price, close=tick.price, volume=tick.size)
            self.candle_history[symbol].append(new_candle)
            if len(self.candle_history[symbol]) > 500: self.candle_history[symbol].pop(0)
        else:
            c = self.candle_history[symbol][-1]
            updated_candle = Candle(
                ts=c.ts,
                open=c.open,
                high=max(c.high, tick.price),
                low=min(c.low, tick.price),
                close=tick.price,
                volume=c.volume + tick.size
            )
            self.candle_history[symbol][-1] = updated_candle

    def process_trade_idea(self, idea: TradeIdea, dt: datetime):
        symbol = idea.symbol
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(dt)
        
        # 1. Crash Protection
        vol = (self.price_history[symbol][-1] * 0.001) if len(self.price_history[symbol]) > 0 else 0.0001
        crash_status = self.crash_module.should_block(symbol, vol, np.eye(1))
        if crash_status["block"]:
            return "REJECTED_CRASH_DEFENSE"

        # 2. Risk & Sizing
        # We need a stop distance for sizing
        stop_dist = abs(idea.entry_price - idea.stop_loss)
        if stop_dist == 0: return "REJECTED_ZERO_STOP"
        
        size = self.risk_engine.get_position_sizing(symbol, vol, self.equity_curve[-1], stop_dist)
        
        valid, msg = self.risk_engine.validate_trade(idea, size, self.equity_curve[-1])
        if not valid: return f"REJECTED_RISK_{msg}"
        
        # 3. Execution
        order = ExecutionOrder(
            id=uuid.uuid4().hex, 
            symbol=symbol, 
            side="buy" if idea.direction == "long" else "sell", 
            price=idea.entry_price, 
            size=size, 
            type="market",
            timestamp=dt
        )
        fill = self.exec_engine.execute(order, session, vol)
        
        # Update Stats
        self.pnl_stats["commissions"] += fill.commission
        self.pnl_stats["slippage_total"] += fill.slippage * abs(fill.fill_size) * spec.contract_size * spec.point_value
        self.pnl_stats["net_pnl"] -= fill.commission

        pos_size = size if idea.direction == "long" else -size
        new_pos = Position(
            symbol=symbol,
            size=pos_size,
            entry_price=fill.fill_price,
            stop_loss=idea.stop_loss,
            take_profit=idea.take_profit,
            entry_ts=dt,
            id=idea.strategy_name # Link to strategy for attribution
        )
        self.open_positions.append(new_pos)
        self.current_positions[symbol] = self.current_positions.get(symbol, 0.0) + pos_size
        self.equity_curve.append(self.equity_curve[-1] - fill.commission)
        
        # Strategy Attribution: record that a position was opened
        return "EXECUTED"

    def _check_exits(self, tick: Tick):
        still_open = []
        for pos in self.open_positions:
            if pos.symbol != tick.symbol:
                still_open.append(pos)
                continue
                
            hit_tp = (pos.size > 0 and tick.price >= pos.take_profit) or (pos.size < 0 and tick.price <= pos.take_profit)
            hit_sl = (pos.size > 0 and tick.price <= pos.stop_loss) or (pos.size < 0 and tick.price >= pos.stop_loss)
            
            if hit_tp or hit_sl:
                self._close_position(pos, tick.price, tick.ts, "TP" if hit_tp else "SL")
            else:
                still_open.append(pos)
        self.open_positions = still_open

    def _handle_gap(self, symbol: str, current_price: float, ts: datetime):
        """Detects gaps across weekends/holidays and adjusts positions."""
        for pos in self.open_positions:
            if pos.symbol == symbol:
                last_price = self.price_history[symbol][-1] if self.price_history[symbol] else pos.entry_price
                gap_size = abs(current_price - last_price)
                if gap_size > (last_price * 0.01): # 1% gap
                    # If gap hits SL/TP, execute at open price (worse for SL, lucky for TP)
                    hit_tp = (pos.size > 0 and current_price >= pos.take_profit) or (pos.size < 0 and current_price <= pos.take_profit)
                    hit_sl = (pos.size > 0 and current_price <= pos.stop_loss) or (pos.size < 0 and current_price >= pos.stop_loss)
                    if hit_tp or hit_sl:
                        self._close_position(pos, current_price, ts, "GAP_EXIT")

    def _apply_corporate_actions(self, symbol: str, ts: datetime):
        spec = self.contract_manager.get_spec(symbol)
        pos_size = self.current_positions.get(symbol, 0.0)
        if pos_size == 0: return

        # Dividends
        if spec.dividend_yield and spec.dividend_yield > 0:
            # Simplified: convert annual yield to daily dividend
            daily_div = (spec.dividend_yield / 365) * spec.contract_size * pos_size
            if daily_div != 0:
                self.equity_curve.append(self.equity_curve[-1] + daily_div)
                self.pnl_stats["dividend_gains"] += daily_div

    def _apply_financing(self, symbol: str, ts: datetime):
        pos = self.current_positions.get(symbol, 0.0)
        if pos == 0: return
        spec = self.contract_manager.get_spec(symbol)
        cost = abs(pos) * (spec.swap_long if pos > 0 else spec.swap_short)
        self.equity_curve.append(self.equity_curve[-1] - cost)
        self.pnl_stats["financing_costs"] += cost

    def _close_position(self, pos: Position, exit_price: float, ts: datetime, reason: str):
        spec = self.contract_manager.get_spec(pos.symbol)
        session = self.contract_manager.get_session(ts)
        vol = (self.price_history[pos.symbol][-1] * 0.001) if len(self.price_history[pos.symbol]) > 0 else 0.0001
        
        # 1. Execution for exit
        side = "sell" if pos.size > 0 else "buy"
        order_type = "stop" if reason in ["SL", "GAP_EXIT"] else "market"
        
        order = ExecutionOrder(
            id=uuid.uuid4().hex,
            symbol=pos.symbol,
            side=side,
            type=order_type,
            price=exit_price,
            size=abs(pos.size),
            timestamp=ts
        )
        fill = self.exec_engine.execute(order, session, vol)
        
        # 2. Realistic PnL Calculation
        raw_pnl = (fill.fill_price - pos.entry_price) * pos.size * spec.contract_size * spec.point_value
        
        # Strategy Attribution
        strat_name = pos.id
        self.strategy_pnl[strat_name] = self.strategy_pnl.get(strat_name, 0.0) + raw_pnl
        
        # Update Stats
        self.pnl_stats["gross_pnl"] += raw_pnl
        self.pnl_stats["net_pnl"] += (raw_pnl - fill.commission)
        self.pnl_stats["commissions"] += fill.commission
        self.pnl_stats["slippage_total"] += fill.slippage * abs(pos.size) * spec.contract_size * spec.point_value

        self.equity_curve.append(self.equity_curve[-1] + raw_pnl - fill.commission)
        self.current_positions[pos.symbol] -= pos.size
        
        self.history.append({
            "type": "EXIT",
            "reason": reason,
            "symbol": pos.symbol,
            "pnl": raw_pnl,
            "ts": ts,
            "strategy": strat_name
        })

    def run(self, ticks: List[Tick]):
        """
        Main backtest loop.
        """
        for tick in ticks:
            self.on_tick(tick)
        
        return self.get_summary()

    def get_summary(self) -> Dict:
        report = PerformanceReporter.generate_report(self.history, self.equity_curve)
        return {
            "pnl_stats": self.pnl_stats,
            "report": report
        }
