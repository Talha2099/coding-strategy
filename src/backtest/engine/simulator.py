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
from src.ml.pattern_recognition.model import PatternRecognizer
from src.core.analytics.factor_engine import FactorEngine

class EventDrivenBacktester:
    def __init__(self, 
                 contract_manager: ContractManager,
                 micro_engine: MicrostructureEngine,
                 fusion_engine: FeatureFusionEngine,
                 meta_model: MetaModel,
                 risk_engine: MultiAssetRiskEngine,
                 exec_engine: ExecutionEngine,
                 trend_module: TrendModule,
                 crash_module: CrashProtectionModule):
        self.contract_manager = contract_manager
        self.micro_engine = micro_engine
        self.fusion_engine = fusion_engine
        self.meta_model = meta_model
        self.risk_engine = risk_engine
        self.exec_engine = exec_engine
        self.trend_module = trend_module
        self.crash_module = crash_module
        self.factor_engine = FactorEngine()
        
        self.history = []
        self.equity_curve = [100000.0]
        self.current_positions: Dict[str, float] = {} # Summary for financing
        self.open_positions: List[Position] = [] # Granular tracking
        self.price_history: Dict[str, List[float]] = {}
        self.last_ts: Dict[str, datetime] = {}
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
            self.last_ts[symbol] = tick.ts
        
        # 0. Gap Detection
        time_diff = (tick.ts - self.last_ts[symbol]).total_seconds()
        if time_diff > 3600 * 24: # More than a day
            self._handle_gap(symbol, tick.price, tick.ts)
        self.last_ts[symbol] = tick.ts

        self.micro_engine.update_trades(tick)
        self.price_history[symbol].append(tick.price)
        if len(self.price_history[symbol]) > 100: self.price_history[symbol].pop(0)
        
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(tick.ts) # Changed ts to match Tick type
        
        # 1. Check Exits (Realistic market-price exits)
        self._check_exits(tick)

        # 2. Factor Analysis update (Forward returns tracking)
        # This belongs in a buffer that waits for future price action
        
        # 3. Trend Analysis
        trend_state = self.trend_module.get_trend_state(symbol, tick.price, self.price_history[symbol])
        
        # 4. Financing & Corporate Actions Check (at 22:00 UTC)
        if tick.ts.hour == 22 and tick.ts.minute == 0:
            self._apply_financing(symbol, tick.ts)
            self._apply_corporate_actions(symbol, tick.ts)

        self.history.append({
            "ts": tick.ts,
            "session": session,
            "trend": trend_state,
            "price": tick.price
        })

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
        
        # Realistic PnL: (Exit - Entry) * Size * ContractSize * PointValue
        price_diff = (exit_price - pos.entry_price)
        if pos.size < 0: price_diff *= -1 # Short logic
        
        raw_pnl = price_diff * abs(pos.size) * spec.contract_size * spec.point_value
        self.pnl_stats["gross_pnl"] += raw_pnl
        self.pnl_stats["net_pnl"] += raw_pnl
        
        self.equity_curve.append(self.equity_curve[-1] + raw_pnl)
        self.current_positions[pos.symbol] -= pos.size
        
        self.history.append({
            "type": "EXIT",
            "reason": reason,
            "symbol": pos.symbol,
            "pnl": raw_pnl,
            "ts": ts
        })

    def process_candidate(self, candidate: TradeCandidate, dt: datetime):
        symbol = candidate.symbol
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(dt)
        
        # 1. Crash Protection
        vol = (self.history[-1]["tick"].price * 0.001) if self.history else 0.0001
        crash_status = self.crash_module.should_block(symbol, vol, np.eye(1))
        if crash_status["block"]:
            return "REJECTED_CRASH_DEFENSE"

        # 2. Trend Filtering
        trend = self.history[-1]["trend"]
        if candidate.direction == "long" and trend["direction"] != 1:
            return "REJECTED_TREND_MISMATCH"
            
        # 3. Meta-Model Scoring
        micro_features = self.micro_engine.compute_features()
        features = self.fusion_engine.build_feature_vector(candidate, micro_features, {
            "trend_strength": trend["strength"],
            "session": session.value,
            "asset_class": spec.asset_class.value
        })
        prob = self.meta_model.predict(features)
        if prob < 0.6: return "REJECTED_META_LABEL"

        # 4. Risk & Sizing
        valid, msg = self.risk_engine.validate_trade(symbol, 1.0, True, self.equity_curve[-1])
        if not valid: return f"REJECTED_RISK_{msg}"
        
        size = self.risk_engine.get_position_sizing(symbol, vol, self.equity_curve[-1], candidate.stop_dist)
        
        # 5. Execution
        order = ExecutionOrder(id=uuid.uuid4().hex, symbol=symbol, side="buy" if candidate.direction == "long" else "sell", price=candidate.entry_zone, size=size, type="market")
        fill = self.exec_engine.execute(order, session, vol)
        
        # Update Stats
        self.pnl_stats["commissions"] += fill.commission
        self.pnl_stats["slippage_total"] += fill.slippage * abs(fill.fill_size) * spec.contract_size * spec.point_value
        self.pnl_stats["net_pnl"] -= fill.commission

        pos_size = size if candidate.direction == "long" else -size
        new_pos = Position(
            symbol=symbol,
            size=pos_size,
            entry_price=fill.fill_price,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            entry_ts=dt,
            id=candidate.id
        )
        self.open_positions.append(new_pos)
        self.current_positions[symbol] = self.current_positions.get(symbol, 0.0) + pos_size
        self.equity_curve.append(self.equity_curve[-1] - fill.commission)
        
        return "EXECUTED"

    def run(self, events: List[Dict]):
        """
        Simple event loop. In research, events would be sorted by timestamp.
        """
        for event in events:
            if event["type"] == "tick":
                self.on_tick(event["data"])
            elif event["type"] == "orderbook":
                self.on_orderbook(event["data"])
            elif event["type"] == "candidate":
                self.process_candidate(event["data"])
