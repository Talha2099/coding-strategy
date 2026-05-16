import pytest
import asyncio
from datetime import datetime
from src.core.contracts.event_state import EventState, EventImportance
from src.data.news.cache import GlobalEventCache
from src.risk.event_overlay import EventRiskOverlay
from src.data.adapters.mt5_adapter import MT5Adapter
from src.data.ingestion.tick_cleaner import TickCleaner
from src.core.types.trading import Tick

def test_news_fallback_policy():
    """Verify that if news is unavailable, the system defaults to technicals (multiplier 1.0)."""
    cache = GlobalEventCache()
    cache.clear() # Ensure clean state
    overlay = EventRiskOverlay()
    
    multiplier, reason = overlay.get_event_adjustment("EURUSD")
    assert multiplier == 1.0
    assert reason is None

def test_news_risk_reduction():
    """Verify that if news is high impact, risk is reduced."""
    cache = GlobalEventCache()
    # Mock high impact event in cache
    state = EventState(
        event_available=True,
        event_importance=EventImportance.HIGH,
        risk_multiplier=0.5
    )
    cache.update_state("EURUSD", state)
    
    overlay = EventRiskOverlay()
    multiplier, reason = overlay.get_event_adjustment("EURUSD")
    assert multiplier == 0.5
    assert "EVENT" in reason

def test_mt5_fast_path_ingestion():
    """Verify MT5 tick ingestion and candle cleaning."""
    cleaner = TickCleaner("EURUSD")
    tick1 = Tick(symbol="EURUSD", bid=1.0, ask=1.01, last=1.005, volume=10, ts=datetime(2024,1,1,10,0,0))
    tick2 = Tick(symbol="EURUSD", bid=1.0, ask=1.01, last=1.006, volume=5, ts=datetime(2024,1,1,10,0,30))
    tick3 = Tick(symbol="EURUSD", bid=1.0, ask=1.01, last=1.004, volume=8, ts=datetime(2024,1,1,10,1,0)) # New minute
    
    is_new1, candle1 = cleaner.process_tick(tick1)
    assert not is_new1
    assert candle1 is None
    
    is_new2, candle2 = cleaner.process_tick(tick2)
    assert not is_new2
    
    is_new3, candle3 = cleaner.process_tick(tick3)
    assert is_new3
    assert candle3 is not None
    assert candle3.open == 1.005
    assert candle3.close == 1.006
    assert candle3.volume == 15

@pytest.mark.asyncio
async def test_async_sidecar_non_blocking():
    """Verify sidecar update doesn't block (simulated by cache check)."""
    from src.data.news.collector import AsyncNewsSidecar
    sidecar = AsyncNewsSidecar(["EURUSD"])
    
    # Run one update cycle
    await sidecar._update_calendar()
    
    cache = GlobalEventCache()
    state = cache.get_state("EURUSD")
    assert state.event_available == True
    assert state.risk_multiplier < 1.0
