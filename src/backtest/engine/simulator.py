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

from src.ml.pattern_recognition.model import PatternRecognizer

from src.core.analytics.factor_engine import FactorEngine

class EventDrivenBacktester:
    def __init__(self, 
                 micro_engine: MicrostructureEngine,
                 fusion_engine: FeatureFusionEngine,
                 meta_model: MetaModel,
                 risk_engine: RiskEngine,
                 exec_engine: ExecutionEngine,
                 pattern_recognizer: PatternRecognizer = None):
        self.micro_engine = micro_engine
        self.fusion_engine = fusion_engine
        self.meta_model = meta_model
        self.risk_engine = risk_engine
        self.exec_engine = exec_engine
        self.pattern_recognizer = pattern_recognizer or PatternRecognizer()
        self.factor_engine = FactorEngine()
        
        self.history = []
        self.pnl = 0.0
        self.equity_curve = [10000.0]
        self.price_history = []
        self.trades_pending_return = [] # To calculate forward returns for factors

    def on_tick(self, tick: Tick):
        self.micro_engine.update_trades(tick)
        self.price_history.append(tick.price)
        if len(self.price_history) > 100: self.price_history.pop(0)
        
        # Check pending returns for factor updates
        self._update_factor_returns(tick.price)

    def _update_factor_returns(self, current_price: float):
        """
        Calculates realized forward returns for pending trade candidates 
        to update factor ICs.
        """
        still_pending = []
        for trade in self.trades_pending_return:
            # If 50 periods have passed, record return
            trade["counter"] += 1
            if trade["counter"] >= 50:
                fwd_return = (current_price - trade["start_price"]) / trade["start_price"]
                if trade["side"] == "sell": fwd_return *= -1
                self.factor_engine.update(trade["features"], fwd_return, trade.get("pnl"))
            else:
                still_pending.append(trade)
        self.trades_pending_return = still_pending

    def on_orderbook(self, snapshot: OrderBookSnapshot):
        self.micro_engine.update_orderbook(snapshot)

    def process_candidate(self, candidate: TradeCandidate, skip_ofi: bool = False):
        """
        The full pipeline execution for a single candidate with factor recording.
        """
        # 1. Compute microstructure features
        micro_features = self.micro_engine.compute_features(skip_ofi=skip_ofi)
        
        # 2. Pattern Recognition
        pattern_data = self.pattern_recognizer.calculate_score(
            candidate, 
            self.price_history, 
            {"entry": candidate.entry_zone}
        )
        pattern_prob = pattern_data["probability"]
        
        # 3. Build features
        features = self.fusion_engine.build_feature_vector(
            candidate, 
            micro_features, 
            {
                "regime_vol": micro_features.realized_volatility,
                "pattern_score": pattern_prob
            }
        )
        
        # 4. Meta-Model Scoring
        prob = self.meta_model.predict(features)
        final_prob = (prob + pattern_prob) / 2
        
        # 5. Create Scored Trade
        scored_trade = ScoredTrade(
            candidate=candidate,
            probability=final_prob,
            expected_return=final_prob * (abs(candidate.take_profit - candidate.entry_zone)),
            risk_score=0.1,
            features=features
        )
        
        # 6. Risk Gating
        if not self.risk_engine.validate(scored_trade):
            return "REJECTED_BY_RISK"
            
        # 7. Execution
        size = self.risk_engine.position_size(scored_trade)
        order_type = self.exec_engine.decide_order_type(scored_trade)
        order = ExecutionOrder(
            id=candidate.id + "_order",
            symbol=candidate.symbol,
            side="buy" if candidate.direction == "long" else "sell",
            type=order_type,
            price=candidate.entry_zone,
            size=size,
            timestamp=datetime.now()
        )
        
        fill = self.exec_engine.execute(order)
        
        # Track PnL (Simplified: entry to TP/SL)
        pnl = (candidate.take_profit - candidate.entry_zone) * size if final_prob > 0.6 else -(candidate.entry_zone - candidate.stop_loss) * size
        self.pnl += pnl
        self.equity_curve.append(self.equity_curve[-1] + pnl)

        # Record for Factor Analysis
        self.trades_pending_return.append({
            "features": features,
            "start_price": candidate.entry_zone,
            "side": candidate.direction,
            "counter": 0,
            "pnl": pnl
        })
        
        self.history.append({
            "candidate": candidate,
            "scored_trade": scored_trade,
            "order": order,
            "fill": fill,
            "pnl": pnl
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
