import pytest
from datetime import datetime
from src.core.types.trading import (
    Tick, OrderBookSnapshot, TradeCandidate, 
    ScoredTrade, ExecutionOrder, FillResult
)
from src.market_microstructure.engine import MicrostructureEngine
from src.features.fusion.engine import FeatureFusionEngine
from src.ml.meta_labeling.model import MetaModel
from src.risk.engine import RiskEngine
from src.execution.engine.base import ExecutionEngine
from src.backtest.engine.simulator import EventDrivenBacktester

def test_full_pipeline_flow():
    # 1. Setup components
    micro = MicrostructureEngine()
    fusion = FeatureFusionEngine()
    meta = MetaModel()
    risk = RiskEngine()
    exec_eng = ExecutionEngine()
    
    backtester = EventDrivenBacktester(micro, fusion, meta, risk, exec_eng)
    
    # 2. Simulate events
    # Market state
    backtester.on_orderbook(OrderBookSnapshot(
        datetime.now(), 
        [(100, 10)], # Bids
        [(100.1, 10)] # Asks: Wide spread, neutral OFI
    ))
    
    # Trade signal from SMC engine
    candidate = TradeCandidate(
        id="test_id",
        symbol="BTCUSDT",
        direction="long",
        entry_zone=100.05,
        stop_loss=99.5,
        take_profit=102.0,
        scenario="fvg_mitigation",
        timestamp=datetime.now()
    )
    
    # 3. Process candidate through pipeline
    result = backtester.process_candidate(candidate)
    
    # Assertions
    assert result == "EXECUTED"
    assert len(backtester.history) == 1
    
    history_entry = backtester.history[0]
    assert history_entry["candidate"].id == "test_id"
    assert "scored_trade" in history_entry
    assert "fill" in history_entry
    assert history_entry["fill"].fill_price > 0

def test_full_pipeline_risk_rejection():
    micro = MicrostructureEngine()
    fusion = FeatureFusionEngine()
    meta = MetaModel()
    risk = RiskEngine(min_prob_threshold=0.9) # High threshold
    exec_eng = ExecutionEngine()
    
    backtester = EventDrivenBacktester(micro, fusion, meta, risk, exec_eng)
    
    # Dummy candidate
    candidate = TradeCandidate("c2", "BTC", "long", 100, 90, 110, "test", datetime.now())
    
    # MetaModel will likely return ~0.5-0.6 heuristic, so it should be rejected
    result = backtester.process_candidate(candidate)
    
    assert result == "REJECTED_BY_RISK"
    assert len(backtester.history) == 0
