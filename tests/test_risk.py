import pytest
from src.risk.engine import RiskEngine
from src.core.types.trading import ScoredTrade, TradeCandidate
from datetime import datetime

def test_risk_gating():
    engine = RiskEngine(min_prob_threshold=0.7)
    
    candidate = TradeCandidate("c1", "BTC", "long", 100, 90, 150, "test", datetime.now())
    
    # Approve trade
    trade_ok = ScoredTrade(candidate, 0.8, 10.0, 0.1, {})
    assert engine.validate(trade_ok) is True
    
    # Reject trade (low probability)
    trade_low = ScoredTrade(candidate, 0.65, 5.0, 0.1, {})
    assert engine.validate(trade_low) is False
    
    # Reject trade (high risk score)
    trade_risky = ScoredTrade(candidate, 0.8, 10.0, 0.9, {})
    assert engine.validate(trade_risky) is False

def test_position_sizing():
    engine = RiskEngine(max_exposure=0.01)
    candidate = TradeCandidate("c1", "BTC", "long", 100, 90, 150, "test", datetime.now())
    trade = ScoredTrade(candidate, 0.8, 10.0, 0.1, {})
    
    size = engine.position_size(trade)
    assert size > 0
    
    # Size should be 0 if rejected
    trade_bad = ScoredTrade(candidate, 0.5, 0, 0.1, {})
    assert engine.position_size(trade_bad) == 0.0
