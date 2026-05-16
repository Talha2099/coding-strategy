from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class StrategyParameters:
    """Standardized parameters for a strategy family on a specific instrument"""
    lookback_window: int = 20
    atr_multiplier: float = 2.0
    stop_multiplier: float = 1.5
    target_multiplier: float = 3.0
    confirmation_threshold: float = 0.5
    min_regime_confidence: float = 0.6
    min_trend_strength: float = 20.0
    max_overextension: float = 2.5
    time_stop_bars: int = 50
    trailing_stop_atr: float = 1.5
    re_entry_delay_bars: int = 10
    invalidation_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BreakoutParams(StrategyParameters):
    rel_vol_threshold: float = 1.5
    acceptance_barrier: float = 0.1 # Distance to barrier for 'acceptance'
    failed_breakout_reclaim: bool = True

@dataclass
class MeanReversionParams(StrategyParameters):
    rsi_extreme_upper: float = 75
    rsi_extreme_lower: float = 25
    zscore_threshold: float = 2.5
    min_volatility_heat: float = 0.15

@dataclass
class TrendParams(StrategyParameters):
    ma_fast: int = 20
    ma_slow: int = 50
    min_persistence: float = 0.6
    pullback_limit_atr: float = 1.0

@dataclass
class RangeParams(StrategyParameters):
    max_adx: float = 20.0
    min_hurst: float = 0.45
    edge_buffer_pct: float = 0.15

@dataclass
class GapParams(StrategyParameters):
    min_gap_size_atr: float = 0.5
    fade_probability_threshold: float = 0.6
