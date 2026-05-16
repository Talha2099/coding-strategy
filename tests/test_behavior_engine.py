import pytest
import numpy as np
from src.core.types.trading import Candle
from src.instruments.behavior_engine import BehaviorEngine
from src.features.technical_engine import TechnicalFeatureEngine
from datetime import datetime

def test_trend_score():
    # Construct a trending candle list
    candles = []
    base_price = 100
    for i in range(150):
        # Strong upward trend
        price = base_price + i * 0.5 + np.random.normal(0, 0.1)
        candles.append(Candle(
            ts=datetime(2023, 1, 1, 0, i),
            open=price-0.2, high=price+0.3, low=price-0.3, close=price,
            volume=1000
        ))
    
    scores = BehaviorEngine.get_behavior_profile(candles, "XAUUSD")
    assert scores["trend_quality"] > 0.6
    assert scores["mean_reversion"] < 0.5

def test_fake_breakout_detection():
    # Construct a rejection candle (large wick + low volume follow through)
    candles = []
    base_price = 100
    for i in range(100):
        price = base_price + np.random.normal(0, 0.1)
        candles.append(Candle(
            ts=datetime(2023, 1, 1, 0, i),
            open=price-0.1, high=price+0.1, low=price-0.1, close=price,
            volume=100
        ))
    
    # The "Breakout" candle with a huge upper wick
    candles.append(Candle(
        ts=datetime(2023, 1, 1, 1, 41),
        open=100.0, high=105.0, low=99.9, close=100.1,
        volume=150 # Low relative volume for such a move
    ))
    
    scores = BehaviorEngine.get_behavior_profile(candles, "XAUUSD")
    # Z-score and wicks should trigger high fakeout prob
    assert scores["fake_breakout_prob"] > 0.5

def test_breakout_quality():
    candles = []
    # Build a tight range (squeeze)
    for i in range(50):
        candles.append(Candle(
            ts=datetime(2023, 1, 1, 0, i),
            open=100, high=100.1, low=99.9, close=100,
            volume=10
        ))
    
    # Real breakout: strong close, high volume
    candles.append(Candle(
        ts=datetime(2023, 1, 1, 0, 51),
        open=100.1, high=102.5, low=100.1, close=102.4,
        volume=1000
    ))
    
    scores = BehaviorEngine.get_behavior_profile(candles, "XAUUSD")
    assert scores["breakout_quality"] > 0.5
    assert scores["fake_breakout_prob"] < 0.4
