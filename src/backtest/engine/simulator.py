import numpy as np
import uuid
from typing import List, Dict
from datetime import datetime
from src.core.types.trading import (
    Candle, Tick, OrderBookSnapshot, 
    TradeCandidate, ScoredTrade, ExecutionOrder, FillResult
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
        self.current_positions: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {}

    def on_tick(self, tick: Tick):
        symbol = tick.symbol
        if symbol not in self.price_history: self.price_history[symbol] = []
        
        self.micro_engine.update_trades(tick)
        self.price_history[symbol].append(tick.price)
        if len(self.price_history[symbol]) > 100: self.price_history[symbol].pop(0)
        
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(tick.timestamp)
        
        # Trend Analysis
        trend_state = self.trend_module.get_trend_state(symbol, tick.price, self.price_history[symbol])
        
        # Financing Check (at 22:00 UTC)
        if tick.timestamp.hour == 22 and tick.timestamp.minute == 0:
            self._apply_financing(symbol)

        self.history.append({
            "tick": tick,
            "session": session,
            "trend": trend_state
        })

    def _apply_financing(self, symbol: str):
        pos = self.current_positions.get(symbol, 0.0)
        if pos == 0: return
        spec = self.contract_manager.get_spec(symbol)
        cost = abs(pos) * (spec.swap_long if pos > 0 else spec.swap_short)
        self.equity_curve.append(self.equity_curve[-1] - cost)

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
        
        pos_change = size if candidate.direction == "long" else -size
        self.current_positions[symbol] = self.current_positions.get(symbol, 0.0) + pos_change
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
