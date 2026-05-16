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

def test_behavior_strategy_routing():
    from src.strategies.registry import StrategyRouter
    from src.regime.engine import RegimeEngine
    from src.core.types.strategy import RegimeType, StrategyFamily
    
    router = StrategyRouter()
    engine = RegimeEngine()
    
    # 1. Trending market
    candles = []
    for i in range(100):
        p = 100 + i * 0.1
        candles.append(Candle(ts=datetime(2023, 1, 1, 0, i), open=p, high=p+0.1, low=p-0.1, close=p, volume=100))
    
    regime_state = engine.classify(candles, "XAUUSD")
    allocations = router.dynamic_strategy_router("XAUUSD", candles, regime_state)
    
    # Trend quality should be high -> Trend allocation high
    assert allocations[StrategyFamily.TREND] > 0.5
    assert allocations[StrategyFamily.MEAN_REVERSION] < 0.5

def test_behavior_risk_adjustment():
    from src.risk.asset_aware_risk import MultiAssetRiskEngine
    from src.core.types.strategy import TradeIdea, StrategyFamily
    from src.core.types.trading import RegimeState
    
    risk = MultiAssetRiskEngine(specs={})
    regime_state = RegimeState(
        symbol="XAUUSD",
        regime_type=RegimeType.CONFIRMED_TREND.value,
        volatility=0.01,
        trend_strength=0.8,
        health_score=0.9,
        lifecycle_stage="mature"
    )
    
    # High confidence trending trade idea
    idea = TradeIdea(
        strategy_name="TrendFollow",
        strategy_family=StrategyFamily.TREND,
        symbol="XAUUSD",
        direction="long",
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=106.0,
        confidence_score=0.8,
        risk_reward_ratio=3.0,
        metadata={}
    )
    
    # Trending candles
    candles = []
    for i in range(100):
        p = 100 + i * 0.1
        candles.append(Candle(ts=datetime(2023, 1, 1, 0, i), open=p, high=p+0.1, low=p-0.1, close=p, volume=100))
    
    size = risk.get_position_sizing(
        "XAUUSD", 0.01, 100000.0, 2.0, regime_state,
        confidence_score=0.8, rr=3.0, candles=candles
    )
    
    # Should be a healthy size
    assert size > 0
