import pytest
from datetime import datetime
from src.scenarios.engine import ScenarioEngine
from src.core.types.trading import Candle

def test_liquidity_sweep_short():
    engine = ScenarioEngine()
    
    # Mock market structure: Previous swing high at 100
    structure = [{'type': 'SH', 'price': 100.0}]
    
    # Current candle: high sweeps 100, close rejects below 100
    candles = [
        Candle(datetime.now(), 90, 105, 85, 95, 1000)
    ]
    
    candidates = engine.evaluate(candles, structure)
    
    assert len(candidates) == 1
    assert candidates[0].direction == "short"
    assert candidates[0].scenario == "liquidity_sweep_reversal"

def test_no_sweep_no_candidate():
    engine = ScenarioEngine()
    structure = [{'type': 'SH', 'price': 100.0}]
    
    # Price doesn't reach 100
    candles = [Candle(datetime.now(), 90, 98, 85, 95, 1000)]
    
    candidates = engine.evaluate(candles, structure)
    assert len(candidates) == 0
