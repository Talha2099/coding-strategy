import pytest
from datetime import datetime
from src.core.types.trading import Candle, Tick
from src.core.types.strategy import RegimeType, StrategyFamily
from src.regime.engine import RegimeEngine
from src.strategies.breakout.donchian import DonchianBreakout
from src.core.contracts.spec import InstrumentSpec, AssetClass

@pytest.fixture
def mock_spec():
    return InstrumentSpec(
        symbol="TEST",
        asset_class=AssetClass.CFD,
        contract_size=100,
        point_value=1.0,
        min_lot=0.01,
        lot_step=0.01,
        allow_short=True
    )

def test_regime_classification():
    engine = RegimeEngine(window=20)
    # Generate 50 candles in a strong bull trend
    candles = [
        Candle(ts=datetime.now(), open=100+i, high=101+i, low=99+i, close=100.5+i, volume=100)
        for i in range(50)
    ]
    regime = engine.classify(candles)
    assert regime in [RegimeType.TRENDING_BULL, RegimeType.BREAKOUT]

def test_donchian_breakout_logic(mock_spec):
    strategy = DonchianBreakout(mock_spec, window=10)
    
    # Range for 10 periods
    candles = [
        Candle(ts=datetime.now(), open=100, high=105, low=95, close=100, volume=100)
        for i in range(11)
    ]
    
    # Breakout candle
    candles.append(Candle(ts=datetime.now(), open=100, high=110, low=100, close=106, volume=200))
    
    setup = strategy.detect_setup(candles, RegimeType.BREAKOUT)
    assert setup is True
    
    idea = strategy.build_trade_idea("TEST", candles, RegimeType.BREAKOUT)
    assert idea.direction == "long"
    assert idea.entry_price == 106
    assert idea.stop_loss < 106
    assert idea.take_profit > 106

def test_strategy_router_selection(mock_spec):
    from src.strategies.registry import StrategyRouter
    router = StrategyRouter()
    strategy = DonchianBreakout(mock_spec, window=10)
    router.register_strategy(strategy)
    
    candles = [Candle(ts=datetime.now(), open=100, high=105, low=95, close=100, volume=100) for i in range(20)]
    
    # Ranging regime - Donchian (Breakout family) should still check setup if is_valid_regime allows
    # In my implementation, is_valid_regime for Breakout returns True if regime.startswith("breakout") OR trending.
    
    ideas = router.get_trade_ideas("TEST", candles, RegimeType.RANGING)
    # DonchianBreakout is_valid_regime: return regime.value.startswith("breakout") or "trending"
    # Ranging is not breakout or trending. So it should return empty list.
    assert len(ideas) == 0
    
    ideas_breakout = router.get_trade_ideas("TEST", candles, RegimeType.BREAKOUT)
    # Even if no actual breakout tick, it checks detect_setup
    assert isinstance(ideas_breakout, list)
