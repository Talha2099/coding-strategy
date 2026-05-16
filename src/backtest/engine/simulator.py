import numpy as np
import uuid
from typing import List, Dict, Optional
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
from src.core.contracts.instrument_spec import InstrumentSpec, SessionType, AssetClass
from src.core.contracts.instrument_registry import InstrumentRegistry
from src.indicators.trend_filter import TrendModule
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.regime.engine import RegimeEngine
from src.regime.mtf_engine import MTFRegimeEngine
from src.strategies.registry import StrategyRouter
from src.core.analytics.reporting import PerformanceReporter
from src.portfolio.router import PortfolioRouter
from src.rl.agents.execution import ExecutionAgent
from src.core.utils.logger import system_logger
from src.backtest.engine.micro_validator import MicrostructureValidator
from src.monitoring.drift_engine import GlobalMonitoringEngine

from src.core.analytics.monitor import StrategyMonitor

class EventDrivenBacktester:
    def __init__(self, 
                 risk_engine: MultiAssetRiskEngine,
                 exec_engine: ExecutionEngine,
                 regime_engine: RegimeEngine,
                 mtf_engine: MTFRegimeEngine,
                 strategy_router: StrategyRouter,
                 crash_module: CrashProtectionModule,
                 portfolio_router: Optional[PortfolioRouter] = None,
                 execution_agent: Optional[ExecutionAgent] = None,
                 meta_model: Optional[MetaModel] = None,
                 micro_validator: Optional[MicrostructureValidator] = None):
        self.risk_engine = risk_engine
        self.exec_engine = exec_engine
        self.regime_engine = regime_engine
        self.mtf_engine = mtf_engine
        self.strategy_router = strategy_router
        self.crash_module = crash_module
        self.portfolio_router = portfolio_router
        self.execution_agent = execution_agent
        self.meta_model = meta_model
        self.micro_validator = micro_validator or MicrostructureValidator()
        self.monitor = StrategyMonitor()
        
        self.history = []
        self.equity_curve = [100000.0]
        self.current_positions: Dict[str, float] = {} # Summary for financing
        self.open_positions: List[Position] = [] # Granular tracking
        self.price_history: Dict[str, List[float]] = {}
        self.candle_history: Dict[str, List[Candle]] = {}
        self.last_ts: Dict[str, datetime] = {}
        
        # Attribution Tracking
        self.strategy_pnl: Dict[str, float] = {} 
        self.regime_pnl: Dict[RegimeType, float] = {rt: 0.0 for rt in RegimeType}
        self.lifecycle_pnl: Dict[str, float] = {}
        self.asset_pnl: Dict[str, float] = {}
        self.session_pnl: Dict[SessionType, float] = {st: 0.0 for st in SessionType}
        
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
        
        spec = InstrumentRegistry.get_spec(symbol)
        session = InstrumentRegistry.get_session(tick.ts, symbol)
        
        # 1. Active Trade Management (RL Agent)
        if self.execution_agent:
            self._manage_active_trades(tick)

        # 3. Regime Analysis
        if len(self.candle_history[symbol]) >= 50:
            regime_state = self.regime_engine.classify(self.candle_history[symbol], symbol)
            regime = RegimeType(regime_state.regime_type)
            self.monitor.add_regime_record(regime.value)
            
            # Phase 13: Monitoring Drift (Moved here so regime is defined)
            vol = (self.price_history[symbol][-1] * 0.001) if len(self.price_history[symbol]) > 0 else 0.0001
            spread = self.exec_engine.get_realtime_spread(symbol, session, regime)
            monitor = GlobalMonitoringEngine.get_monitor(symbol)
            monitor.record_market_state(spread, vol)
            
            # Record Behavior Scores
            from src.instruments.behavior_engine import BehaviorEngine
            b_scores = BehaviorEngine.get_behavior_profile(self.candle_history[symbol], symbol)
            monitor.record_behavior_scores(b_scores)
            
            # MTF Regime Analysis
            mtf_state = self.mtf_engine.analyze(
                ltf_candles=self.candle_history[symbol],
                mtf_candles=self.candle_history[symbol], # Should be resampled
                htf_candles=self.candle_history[symbol]  # Should be resampled
            )
        else:
            regime_state = self.regime_engine._default_state(symbol)
            regime = RegimeType.VOLATILE_UNSTABLE # Initial state
            mtf_state = None
        
        # 2. Check Static Exits (SL/TP) - Moved after regime calculation
        self._check_exits(tick, regime)

        if self.history and self.history[-1].get("regime") != regime:
            system_logger.log_event("REGIME_CHANGE", {
                "symbol": symbol,
                "old_regime": str(self.history[-1].get("regime")),
                "new_regime": regime.name,
                "ts": tick.ts.isoformat()
            })

        # 4. Strategy Scan & Portfolio Orchestration (Phase 12)
        all_ideas = self.strategy_router.get_trade_ideas(symbol, self.candle_history[symbol], regime_state, mtf_state)
        
        if self.portfolio_router:
            # Note: For multi-symbol simulation, this would look at all pending ideas across symbols
            # In this tick-by-tick loop, it filters the current symbol's potential setups
            optimized_ideas = self.portfolio_router.route_ideas(all_ideas, {symbol: regime_state}, self.equity_curve[-1])
        else:
            optimized_ideas = all_ideas
        
        for idea in optimized_ideas:
            self.process_trade_idea(idea, tick.ts, regime, regime_state)
        
        # 5. Financing & Corporate Actions Check (at 22:00 UTC)
        if tick.ts.hour == 22 and tick.ts.minute == 0:
            self._apply_financing(symbol, tick.ts)
            self._apply_corporate_actions(symbol, tick.ts)

        self.history.append({
            "ts": tick.ts,
            "session": session,
            "regime": regime,
            "price": tick.price
        })

    def _manage_active_trades(self, tick: Tick):
        """Delegates active management to the Execution Agent."""
        for pos in self.open_positions:
            if pos.symbol == tick.symbol:
                action = self.execution_agent.manage_position(pos, self.candle_history[tick.symbol])
                if action == "CLOSE":
                    self._close_position(pos, tick.price, tick.ts, "RL_EXIT")

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

    def process_trade_idea(self, idea: TradeIdea, dt: datetime, regime: RegimeType, regime_state: RegimeState):
        symbol = idea.symbol
        spec = InstrumentRegistry.get_spec(symbol)
        session = InstrumentRegistry.get_session(dt, symbol)
        
        # 1. Crash Protection
        vol = (self.price_history[symbol][-1] * 0.001) if len(self.price_history[symbol]) > 0 else 0.0001
        crash_status = self.crash_module.should_block(symbol, vol, np.eye(1))
        if crash_status["block"]:
            system_logger.log_event("SETUP_REJECTION", {"reason": "CRASH_DEFENSE", "symbol": symbol, "ts": dt.isoformat()})
            return "REJECTED_CRASH_DEFENSE"

        # 2. Risk & Sizing (Now Kelly-aware)
        stop_dist = abs(idea.entry_price - idea.stop_loss)
        if stop_dist == 0: return "REJECTED_ZERO_STOP"
        
        # 2.1 Spread Check from Execution Engine
        spread = self.exec_engine.get_realtime_spread(symbol, session, regime)
        valid_exec, exec_msg = self.exec_engine.validate_for_execution(
             ExecutionOrder("", idea.symbol, "buy", "market", None, 0.0, dt), 
             spread, 
             regime
        )
        if not valid_exec:
             system_logger.log_event("EXECUTION_REJECTION", {"reason": exec_msg, "symbol": symbol, "ts": dt.isoformat()})
             return f"REJECTED_EXEC_{exec_msg}"

        size = self.risk_engine.get_position_sizing(
            symbol, vol, self.equity_curve[-1], stop_dist, regime_state,
            idea=idea,
            confidence_score=idea.confidence_score,
            rr=idea.risk_reward_ratio,
            candles=self.candle_history[symbol]
        )
        
        valid, msg = self.risk_engine.validate_trade(
            idea, size, self.equity_curve[-1], regime_state, 
            current_spread=spec.cost_model.spread_fixed,
            candles=self.candle_history[symbol]
        )
        if not valid: 
            system_logger.log_event("RISK_REJECTION", {"reason": msg, "symbol": symbol, "ts": dt.isoformat()})
            return f"REJECTED_RISK_{msg}"
        
        # 2.5 Microstructure Validation (Optional)
        micro_conf = self.micro_validator.validate_idea(idea, None)
        if not micro_conf["valid"]:
            system_logger.log_event("MICRO_REJECTION", {"reason": micro_conf["reason"], "symbol": symbol, "ts": dt.isoformat()})
            return f"REJECTED_MICRO_{micro_conf['reason']}"

        # 3. Execution
        entry_price = idea.entry_price
        if self.execution_agent:
            entry_price = self.execution_agent.optimize_entry(idea.entry_price, idea.entry_price)
        
        # PHASE 13: Behavior-Aware Execution in Backtest
        from src.instruments.behavior_engine import BehaviorEngine
        b_scores = BehaviorEngine.get_behavior_profile(self.candle_history[symbol], symbol)
        
        order = ExecutionOrder(
            id=uuid.uuid4().hex, 
            symbol=symbol, 
            side="buy" if idea.direction == "long" else "sell", 
            price=entry_price, 
            size=size, 
            type="market",
            timestamp=dt
        )
        fill = self.exec_engine.execute_at_tick(order, entry_price, session, vol, regime=regime, b_scores=b_scores)
        if not fill: return "EXECUTION_FAILED"
        
        # Record execution for drift monitor
        GlobalMonitoringEngine.get_monitor(symbol).record_execution(fill)
        
        system_logger.log_event("ORDER_FILLED", {
            "symbol": symbol,
            "side": order.side,
            "price": fill.fill_price,
            "size": fill.fill_size,
            "strategy": idea.strategy_name,
            "regime": regime.name
        })

        # Update Stats
        self.pnl_stats["commissions"] += fill.commission
        self.pnl_stats["slippage_total"] += fill.slippage * abs(fill.fill_size) * spec.contract_size * spec.point_value
        self.pnl_stats["net_pnl"] -= fill.commission

        pos_size = fill.fill_size if idea.direction == "long" else -fill.fill_size
        new_pos = Position(
            id=idea.strategy_name,
            symbol=symbol,
            asset_class=spec.asset_class.name,
            size=pos_size,
            entry_price=fill.fill_price,
            avg_price=fill.fill_price,
            stop_loss=idea.stop_loss,
            take_profit=idea.take_profit,
            entry_ts=dt,
            strategy_name=idea.strategy_name,
            regime_at_entry=regime,
            session_at_entry=session,
            lifecycle_phase_at_entry=getattr(idea, "lifecycle_phase", "unknown"),
            metadata={
                "trend_stage": regime_state.lifecycle_stage,
                "health": regime_state.health_score,
                "slippage": fill.slippage * abs(fill.fill_size) * spec.contract_size * spec.point_value
            }
        )
        self.open_positions.append(new_pos)
        self.current_positions[symbol] = self.current_positions.get(symbol, 0.0) + pos_size
        self.equity_curve.append(self.equity_curve[-1] - fill.commission)
        
        return "EXECUTED"

    def _check_exits(self, tick: Tick, current_regime: RegimeType):
        still_open = []
        for pos in self.open_positions:
            if pos.symbol != tick.symbol:
                still_open.append(pos)
                continue
                
            hit_tp = (pos.size > 0 and tick.price >= pos.take_profit) or (pos.size < 0 and tick.price <= pos.take_profit)
            hit_sl = (pos.size > 0 and tick.price <= pos.stop_loss) or (pos.size < 0 and tick.price >= pos.stop_loss)
            
            if hit_tp or hit_sl:
                self._close_position(pos, tick.price, tick.ts, "TP" if hit_tp else "SL", current_regime)
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
        spec = InstrumentRegistry.get_spec(symbol)
        pos_size = self.current_positions.get(symbol, 0.0)
        if pos_size == 0: return

        # Dividends
        div_yield = spec.metadata.get("dividend_yield", 0.0)
        if div_yield > 0:
            daily_div = (div_yield / 365) * spec.contract_size * pos_size
            if daily_div != 0:
                self.equity_curve.append(self.equity_curve[-1] + daily_div)
                self.pnl_stats["dividend_gains"] += daily_div

    def _apply_financing(self, symbol: str, ts: datetime):
        pos = self.current_positions.get(symbol, 0.0)
        if pos == 0: return
        spec = InstrumentRegistry.get_spec(symbol)
        cost = abs(pos) * (spec.cost_model.swap_long if pos > 0 else spec.cost_model.swap_short)
        self.equity_curve.append(self.equity_curve[-1] - cost)
        self.pnl_stats["financing_costs"] += cost

    def _close_position(self, pos: Position, exit_price: float, ts: datetime, reason: str, current_regime: Optional[RegimeType] = None):
        spec = InstrumentRegistry.get_spec(pos.symbol)
        session = InstrumentRegistry.get_session(ts, pos.symbol)
        vol = (self.price_history[pos.symbol][-1] * 0.001) if len(self.price_history[pos.symbol]) > 0 else 0.0001
        regime = current_regime or pos.regime_at_entry # Fallback to entry regime if current is unknown
        
        # 1. Execution for exit
        side = "sell" if pos.size > 0 else "buy"
        order_type = "stop" if reason in ["SL", "GAP_EXIT"] else "market"
        
        # PHASE 13: Behavior-Aware Exit
        from src.instruments.behavior_engine import BehaviorEngine
        b_scores = BehaviorEngine.get_behavior_profile(self.candle_history[pos.symbol], pos.symbol)
        
        order = ExecutionOrder(
            id=uuid.uuid4().hex,
            symbol=pos.symbol,
            side=side,
            type=order_type,
            price=exit_price,
            size=abs(pos.size),
            timestamp=ts
        )
        fill = self.exec_engine.execute_at_tick(order, exit_price, session, vol, regime=regime, b_scores=b_scores)
        if not fill: return # Exit failed in simulation
        # 2. Realistic PnL Calculation
        raw_pnl = (fill.fill_price - pos.entry_price) * pos.size * spec.contract_size * spec.point_value
        
        # Attribution
        strat_name = pos.id
        self.strategy_pnl[strat_name] = self.strategy_pnl.get(strat_name, 0.0) + raw_pnl
        self.regime_pnl[pos.regime_at_entry] += raw_pnl
        self.lifecycle_pnl[pos.lifecycle_phase_at_entry] = self.lifecycle_pnl.get(pos.lifecycle_phase_at_entry, 0.0) + raw_pnl
        self.asset_pnl[pos.asset_class] = self.asset_pnl.get(pos.asset_class, 0.0) + raw_pnl
        self.session_pnl[pos.session_at_entry] += raw_pnl
        
        system_logger.log_event("TRADE_CLOSED", {
            "symbol": pos.symbol,
            "reason": reason,
            "pnl": raw_pnl,
            "strategy": strat_name,
            "regime": pos.regime_at_entry.name,
            "ts": ts.isoformat()
        })

        # Update Stats
        self.pnl_stats["gross_pnl"] += raw_pnl
        self.pnl_stats["net_pnl"] += (raw_pnl - fill.commission)
        self.pnl_stats["commissions"] += fill.commission
        self.pnl_stats["slippage_total"] += fill.slippage * abs(pos.size) * spec.contract_size * spec.point_value

        self.equity_curve.append(self.equity_curve[-1] + raw_pnl - fill.commission)
        self.current_positions[pos.symbol] -= pos.size
        
        exit_record = {
            "type": "EXIT",
            "reason": reason,
            "symbol": pos.symbol,
            "pnl": raw_pnl,
            "ts": ts,
            "strategy": strat_name,
            "regime": pos.regime_at_entry,
            "session": pos.session_at_entry,
            "asset_class": pos.asset_class,
            "trend_stage": pos.metadata.get("trend_stage"),
            "health": pos.metadata.get("health"),
            "slippage": pos.metadata.get("slippage", 0.0)
        }
        self.history.append(exit_record)
        self.monitor.add_trade_record(exit_record)

    def run(self, ticks: List[Tick]):
        """
        Main backtest loop.
        """
        for tick in ticks:
            self.on_tick(tick)
        
        return self.get_summary()

    def get_summary(self) -> Dict:
        report = PerformanceReporter.generate_report(self.history, self.equity_curve)
        health = self.monitor.get_health_report()
        drift_report = GlobalMonitoringEngine.run_daily_audit()
        
        # Phase 9: Research outputs split by instrument, asset class, etc.
        return {
            "pnl_stats": self.pnl_stats,
            "report": report,
            "health": health,
            "drift": drift_report,
            "splits": {
                "instrument": self.asset_pnl,
                "asset_class": self.asset_pnl, # Already tracking by name
                "strategy": self.strategy_pnl,
                "regime": {k.name: v for k, v in self.regime_pnl.items()},
                "session": {k.name: v for k, v in self.session_pnl.items()},
                "lifecycle_phase": self.lifecycle_pnl
            }
        }
