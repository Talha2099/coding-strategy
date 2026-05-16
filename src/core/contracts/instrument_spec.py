from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import time

class AssetClass(Enum):
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"
    EQUITY = "equity"
    CRYPTO = "crypto"

class InstrumentType(Enum):
    SPOT = "spot"
    CFD = "cfd"
    FUTURE = "future"
    OPTION = "option"

class SessionType(Enum):
    ASIA = "asia"
    LONDON = "london"
    NEW_YORK = "new_york"
    LATE_NY = "late_ny"
    OVERNIGHT = "overnight"

@dataclass
class TradingSession:
    name: SessionType
    start_time: time
    end_time: time
    is_primary_liquidity: bool = False

@dataclass
class CostModel:
    spread_fixed: float = 0.0
    spread_variable_mult: float = 1.0  # Multiplier for volatility-based spread
    commission_per_lot: float = 0.0
    slippage_base_bps: float = 0.5
    swap_long: float = 0.0
    swap_short: float = 0.0
    # Phase 8 Additions
    execution_type_preference: str = "market" # market, limit
    partial_fill_likelihood: float = 1.0
    gap_fill_likelihood: float = 0.5
    session_spread_multipliers: Dict[SessionType, float] = field(default_factory=dict)

class Archetype(Enum):
    GOLD_CFD = "gold_cfd"
    INDEX_CFD = "index_cfd"
    US_LARGE_CAP = "us_large_cap"
    US_SMALL_CAP = "us_small_cap"
    HIGH_BETA = "high_beta"
    LOW_BETA = "low_beta"
    GAP_HEAVY = "gap_heavy"
    TREND_HEAVY = "trend_heavy"
    MEAN_REVERTING = "mean_reverting"
    RANGE_HEAVY = "range_heavy"
    NEWS_SENSITIVE = "news_sensitive"
    # New Archetypes from YAML
    MACRO_SENSITIVE = "macro_sensitive"
    LIQUIDITY_DRIVEN = "liquidity_driven"
    VOLATILITY_EXPANSION = "volatility_expansion"
    INSTITUTIONAL_MOMENTUM = "institutional_momentum"
    MOMENTUM_INDEX = "momentum_index"
    GROWTH_SENTIMENT = "growth_sentiment"
    TREND_PERSISTENT = "trend_persistent"
    MACRO_SENTIMENT_INDEX = "macro_sentiment_index"
    INSTITUTIONAL_ROTATION = "institutional_rotation"
    BALANCED_TREND_MR = "balanced_trend_mr"
    HIGH_VOL_FX = "high_vol_fx"
    CARRY_TRADE_SENSITIVE = "carry_trade_sensitive"
    TREND_EXPANSION = "trend_expansion"
    LIQUIDITY_SWEEP_PRONE = "liquidity_sweep_prone"

@dataclass
class AssetBehavior:
    """Quantitative behavior DNA of an instrument"""
    archetype: Archetype
    archetypes: List[Archetype] = field(default_factory=list) # Phase 13 extension
    trend_persistence: float = 0.5    # 0 to 1
    mean_reversion_propensity: float = 0.5
    volatility_regime_avg: float = 0.2 # Annualized vol
    gap_frequency: float = 0.1        # Probability of morning gaps
    breakout_success_rate: float = 0.3
    news_sensitivity: float = 0.5
    session_dependency: Dict[SessionType, float] = field(default_factory=dict)
    typical_range_atr_mult: float = 2.0
    failure_modes: List[str] = field(default_factory=list) # e.g. ["v_reversal", "stop_run", "gap_and_crap"]
    preferred_timeframes: List[str] = field(default_factory=lambda: ["5m", "15m", "1h"])
    event_risk_sensitivity: float = 0.5 # Added for Phase 7
    short_penalty_multiplier: float = 1.0 # Added for Phase 7 (for stocks etc)
    # Phase 13 extensions
    volatility_clustering: bool = True
    trend_acceleration: float = 0.5
    exhaustion_reversal_prob: float = 0.5
    late_trend_risk: float = 0.5
    breakout_quality: float = 0.5
    false_breakout_prob: float = 0.5
    confirmation_requirement: str = "NORMAL" # NORMAL, STRICT
    stop_hunt_probability: float = 0.5

@dataclass
class InstrumentSpec:
    symbol: str
    asset_class: AssetClass
    instrument_type: InstrumentType
    
    # Technical Specs
    tick_size: float
    point_value: float
    contract_size: float
    lot_step: float
    min_lot: float
    max_lot: float
    
    # Costs & Risk
    cost_model: CostModel
    margin_requirement: float  # e.g. 0.05 for 1:20
    leverage_limit: int
    allow_overnight: bool = True # Added for Phase 7
    allow_short: bool = True     # Added for Phase 7
    stop_widening_factor: float = 1.0 # Added for Phase 7
    
    # Behavior & Strategy Alignment
    behavior: AssetBehavior
    preferred_strategies: List[str] = field(default_factory=list)
    restricted_strategies: List[str] = field(default_factory=list)
    
    # Temporal Components
    sessions: List[TradingSession] = field(default_factory=list)
    base_currency: str = "USD"
    quote_currency: str = "USD"
    
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_pip_value(self, lot_size: float) -> float:
        return (self.tick_size * self.contract_size) * lot_size
