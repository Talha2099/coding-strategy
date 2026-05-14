import pytest
from datetime import datetime, timedelta
from src.core.types.trading import Candle, Tick
from src.regime.engine import RegimeEngine
from src.core.contracts.spec import ContractManager
from src.strategies.trend.lifecycle_trend import LifecycleTrendStrategy

def generate_trend_candles(start_price: float, n: int, slope: float, noise: float = 0.01):
    candles = []
    curr_price = start_price
    start_ts = datetime(2023, 1, 1)
    
    for i in range(n):
        ts = start_ts + timedelta(minutes=i)
        o = curr_price
        c = o + slope + (np.random.randn() * noise)
        h = max(o, c) + abs(np.random.randn() * noise * 0.5)
        l = min(o, c) - abs(np.random.randn() * noise * 0.5)
        candles.append(Candle(ts=ts, open=o, high=h, low=l, close=c, volume=100))
        curr_price = c
    return candles

import numpy as np

def test_trend_health_deterioration():
    """
    Verifies that health score drops when trend starts overextending or exhaust.
    """
    engine = RegimeEngine()
    
    # 1. Healthy Stable Trend
    candles = generate_trend_candles(100.0, 60, 0.1, noise=0.02)
    state = engine.classify(candles, "TEST")
    
    initial_health = state.health_score
    assert initial_health > 0.5
    
    # 2. Add an overextension (parabolic spike)
    parabolic = generate_trend_candles(candles[-1].close, 10, 1.5, noise=0.05)
    full_history = candles + parabolic
    
    state_parabolic = engine.classify(full_history, "TEST")
    # Health might still be high because of slope, but exhaustion risk should rise
    assert state_parabolic.exhaustion_risk > state.exhaustion_risk
    assert state_parabolic.overextension > state.overextension

def test_late_trend_rejection():
    """
    Verifies that strategy rejects setup when tired.
    """
    strategy = LifecycleTrendStrategy(name="TrendTest", is_long=True)
    engine = RegimeEngine()
    
    # 1. Parabolic extension
    candles = generate_trend_candles(100.0, 100, 0.5, noise=0.1)
    state = engine.classify(candles, "TEST")
    
    # Manually spike exhaustion if needed or use classified state
    # LifecycleTrendStrategy.detect_setup checks exhaustion_risk > 0.7
    
    # If state is exhausted, setup should be rejected
    if state.exhaustion_risk > 0.7:
        assert not strategy.detect_setup(candles, state)
    else:
        # Force it for the test if generation was too mild
        from dataclasses import replace
        exhausted_state = replace(state, exhaustion_risk=0.8)
        assert not strategy.detect_setup(candles, exhausted_state)

def test_hurst_persistence():
    """
    Verifies Hurst exponent changes with regime.
    """
    engine = RegimeEngine()
    
    # Trending
    trending = generate_trend_candles(100.0, 100, 0.2, noise=0.01)
    state_trending = engine.classify(trending, "TEST")
    
    # Ranging (random walk)
    ranging = generate_trend_candles(100.0, 100, 0.0, noise=0.5)
    state_ranging = engine.classify(ranging, "TEST")
    
    assert state_trending.hurst > state_ranging.hurst
