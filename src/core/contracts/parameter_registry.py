from typing import Dict, Type, Any
from src.core.contracts.strategy_params import (
    StrategyParameters, BreakoutParams, MeanReversionParams, 
    TrendParams, RangeParams, GapParams
)
from src.core.types.strategy import StrategyFamily
from src.core.contracts.instrument_spec import Archetype

class ParameterRegistry:
    """Stores and retrieves instrument-specific strategy parameters"""
    
    _matrix: Dict[Archetype, Dict[StrategyFamily, StrategyParameters]] = {}

    @classmethod
    def register(cls, archetype: Archetype, family: StrategyFamily, params: StrategyParameters):
        if archetype not in cls._matrix:
            cls._matrix[archetype] = {}
        cls._matrix[archetype][family] = params

    @classmethod
    def get_params(cls, archetype: Archetype, family: StrategyFamily) -> StrategyParameters:
        # 1. Look for specific archetype+family match
        if archetype in cls._matrix and family in cls._matrix[archetype]:
            return cls._matrix[archetype][family]
        
        # 2. Return reasonable defaults based on family if not found
        return cls._get_default_for_family(family)

    @classmethod
    def _get_default_for_family(cls, family: StrategyFamily) -> StrategyParameters:
        if family == StrategyFamily.BREAKOUT: return BreakoutParams()
        if family == StrategyFamily.TREND: return TrendParams()
        if family == StrategyFamily.MEAN_REVERSION: return MeanReversionParams()
        if family == StrategyFamily.RANGE: return RangeParams()
        return StrategyParameters()

# Bootstrap some Archetype-specific parameters
ParameterRegistry.register(
    Archetype.GOLD_CFD, 
    StrategyFamily.BREAKOUT, 
    BreakoutParams(atr_multiplier=3.0, stop_multiplier=2.0) # Gold needs wider stops
)

ParameterRegistry.register(
    Archetype.INDEX_CFD,
    StrategyFamily.TREND,
    TrendParams(min_trend_strength=25.0, ma_fast=10, ma_slow=30) # Fast indices
)

ParameterRegistry.register(
    Archetype.RANGE_HEAVY,
    StrategyFamily.RANGE,
    RangeParams(max_adx=25.0, edge_buffer_pct=0.2)
)
