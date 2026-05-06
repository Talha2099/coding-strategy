from typing import List, Dict
from datetime import datetime
from src.core.types.trading import (
    Candle, Tick, OrderBookSnapshot, 
    TradeCandidate, ScoredTrade, ExecutionOrder, FillResult
)
from src.market_microstructure.engine import MicrostructureEngine
from src.features.fusion.engine import FeatureFusionEngine
from src.ml.meta_labeling.model import MetaModel
from src.risk.engine import RiskEngine
from src.execution.engine.base import ExecutionEngine

class EventDrivenBacktester:
    def __init__(self, 
                 micro_engine: MicrostructureEngine,
                 fusion_engine: FeatureFusionEngine,
                 meta_model: MetaModel,
                 risk_engine: RiskEngine,
                 exec_engine: ExecutionEngine):
        self.micro_engine = micro_engine
        self.fusion_engine = fusion_engine
        self.meta_model = meta_model
        self.risk_engine = risk_engine
        self.exec_engine = exec_engine
        
        self.history = []
        self.pnl = 0.0

    def on_tick(self, tick: Tick):
        self.micro_engine.update_trades(tick)

    def on_orderbook(self, snapshot: OrderBookSnapshot):
        self.micro_engine.update_orderbook(snapshot)

    def process_candidate(self, candidate: TradeCandidate):
        """
        The full pipeline execution for a single candidate.
        """
        # 1. Compute microstructure features
        micro_features = self.micro_engine.compute_features()
        
        # 2. Build feature vector (Fusion)
        features = self.fusion_engine.build_feature_vector(
            candidate, 
            micro_features, 
            {"regime_vol": micro_features.realized_volatility}
        )
        
        # 3. Model Scoring
        prob = self.meta_model.predict(features)
        
        # 4. Create Scored Trade
        scored_trade = ScoredTrade(
            candidate=candidate,
            probability=prob,
            expected_return=prob * (abs(candidate.take_profit - candidate.entry_zone)), # Simple EV
            risk_score=0.1, # Dummy
            features=features
        )
        
        # 5. Risk Gating
        if not self.risk_engine.validate(scored_trade):
            return "REJECTED_BY_RISK"
            
        # 6. Position Sizing
        size = self.risk_engine.position_size(scored_trade)
        
        # 7. Execution Decision
        order_type = self.exec_engine.decide_order_type(scored_trade)
        
        # 8. Create Execution Order
        order = ExecutionOrder(
            id=candidate.id + "_order",
            symbol=candidate.symbol,
            side="buy" if candidate.direction == "long" else "sell",
            type=order_type,
            price=candidate.entry_zone,
            size=size,
            timestamp=datetime.now()
        )
        
        # 9. Execute (Simulation)
        fill = self.exec_engine.execute(order)
        
        self.history.append({
            "candidate": candidate,
            "scored_trade": scored_trade,
            "order": order,
            "fill": fill
        })
        
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
