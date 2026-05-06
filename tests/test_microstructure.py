import pytest
from datetime import datetime
from src.core.types.trading import Tick, OrderBookSnapshot
from src.market_microstructure.engine import MicrostructureEngine

def test_microstructure_compute():
    engine = MicrostructureEngine()
    
    # Mock snapshot
    snapshot = OrderBookSnapshot(
        ts=datetime.now(),
        bids=[(100.0, 10.0), (99.0, 20.0)],
        asks=[(101.0, 10.0), (102.0, 20.0)]
    )
    engine.update_orderbook(snapshot)
    
    features = engine.compute_features()
    
    assert features.spread == 1.0
    assert features.mid_price == 100.5
    assert features.imbalance == 0.0 # (30-30)/60

def test_ofi_calculation():
    engine = MicrostructureEngine()
    engine.update_orderbook(OrderBookSnapshot(datetime.now(), [(100, 10)], [(101, 10)]))
    
    engine.update_trades(Tick(datetime.now(), 100.5, 5.0, "buy"))
    engine.update_trades(Tick(datetime.now(), 100.5, 2.0, "sell"))
    
    features = engine.compute_features()
    # (5 - 2) / (5 + 2) = 3/7 = 0.428...
    assert round(features.order_flow_imbalance, 2) == 0.43
