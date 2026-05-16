import pytest
from datetime import datetime
from src.core.contracts.instrument_registry import InstrumentRegistry
from src.core.contracts.instrument_spec import AssetClass, SessionType
from src.core.types.strategy import StrategyFamily, RegimeType
from src.core.contracts.strategy_matrix import StrategyCompatibilityMatrix
from src.core.contracts.strategy_params import StrategyParameterRegistry
from src.risk.asset_aware_risk import MultiAssetRiskEngine
from src.core.types.strategy import TradeIdea

def test_instrument_registry_loading():
    """Verify primary instruments are correctly registered with their profiles."""
    gold = InstrumentRegistry.get_spec("XAUUSD")
    assert gold is not None
    assert gold.asset_class == AssetClass.COMMODITY
    assert gold.behavior.archetype.value == "sweep_prone"
    
    spx = InstrumentRegistry.get_spec("SPX500")
    assert spx is not None
    assert spx.asset_class == AssetClass.INDEX
    assert spx.behavior.news_sensitivity > 0.7

def test_strategy_compatibility_matrix():
    """Verify that strategies are correctly prioritized based on instrument behavior."""
    # Trend Following on Trend Heavy Instrument (SPX)
    spx_spec = InstrumentRegistry.get_spec("SPX500")
    score_trend = StrategyCompatibilityMatrix.get_suitability_score(
        strategy_family=StrategyFamily.TREND,
        archetype=spx_spec.behavior.archetype,
        regime=RegimeType.CONFIRMED_TREND,
        session=SessionType.LONDON,
        volatility=0.2,
        trend_strength=0.8
    )
    assert score_trend > 0.8
    
    # Range Fade on Trend Heavy Instrument (SPX) in Trend Regime
    score_range = StrategyCompatibilityMatrix.get_suitability_score(
        strategy_family=StrategyFamily.RANGE,
        archetype=spx_spec.behavior.archetype,
        regime=RegimeType.CONFIRMED_TREND,
        session=SessionType.LONDON,
        volatility=0.2,
        trend_strength=0.8
    )
    assert score_range < 0.3

def test_instrument_specific_params():
    """Verify that different instruments retrieve different strategy parameters."""
    gold_params = StrategyParameterRegistry.get_params(StrategyFamily.BREAKOUT, "XAUUSD")
    stock_params = StrategyParameterRegistry.get_params(StrategyFamily.BREAKOUT, "AAPL")
    
    # Gold usually needs much wider targets/stops than generic stocks
    assert gold_params.target_multiplier > stock_params.target_multiplier

def test_risk_engine_asset_awareness():
    """Verify risk engine applies asset-specific constraints."""
    risk_engine = MultiAssetRiskEngine()
    gold_spec = InstrumentRegistry.get_spec("XAUUSD")
    
    idea = TradeIdea(
        symbol="XAUUSD",
        strategy_name="test",
        direction="long",
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2030.0,
        confidence_score=0.8,
        strategy_family=StrategyFamily.BREAKOUT
    )
    
    # Test shorting restriction if it existed
    # In our current specAAPL has low short penalty, but let's test a hypothetical
    from src.core.contracts.asset_profile import AssetProfileFactory
    stock_spec = AssetProfileFactory.create_stock_spec("DANGER")
    stock_spec.behavior.short_penalty_multiplier = 2.0
    InstrumentRegistry.register(stock_spec)
    
    short_idea = TradeIdea(
        symbol="DANGER",
        strategy_name="test",
        direction="short",
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=80.0,
        confidence_score=0.8,
        strategy_family=StrategyFamily.BREAKOUT
    )
    
    valid, msg = risk_engine.validate_trade(short_idea, 10.0, 100000.0, None, 0.1)
    assert not valid
    assert "SHORTING_RISK_TOO_HIGH" in msg

def test_session_aware_execution_costs():
    """Verify execution costs change by session as per instrument spec."""
    from src.execution.engine.base import ExecutionEngine
    exec_engine = ExecutionEngine()
    
    # EURUSD spread in London vs Late NY (hypothetical drift/session logic)
    # Based on our AssetProfile for EURUSD: Asia: 2.0, NY: 1.0, London: 1.0
    spread_london = exec_engine.get_realtime_spread("EURUSD", SessionType.LONDON)
    spread_asia = exec_engine.get_realtime_spread("EURUSD", SessionType.ASIA)
    
    assert spread_asia > spread_london
