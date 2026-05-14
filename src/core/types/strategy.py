from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Literal, Any

class RegimeType(Enum):
    # Trend States
    NO_TREND = "no_trend"
    PRE_TREND_COMPRESSION = "pre_trend_compression"
    EARLY_TREND = "early_trend"
    CONFIRMED_TREND = "confirmed_trend"
    MID_TREND = "mid_trend"
    PULLBACK_IN_TREND = "pullback_in_trend"
    CONTINUATION_READY = "continuation_ready"
    LATE_TREND = "late_trend"
    EXHAUSTION_RISK = "exhaustion_risk"
    REVERSAL_RISK = "reversal_risk"
    TREND_FAILED = "trend_failed"
    TREND_TO_RANGE = "trend_to_range"
    
    # Directional Trend tags (for strategy decisions)
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    
    # Other States
    RANGE = "range"
    BREAKOUT_PREP = "breakout_prep"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE_UNSTABLE = "volatile_unstable"
    GAP_DRIVEN = "gap_driven"
    
    # Breakout Lifecycle
    BREAKOUT_ACTIVE = "breakout_active"
    POST_BREAKOUT_CONTINUATION = "post_breakout_continuation"
    FALSE_BREAKOUT_RISK = "false_breakout_risk"
    
    # Range Lifecycle States
    RANGE_FORMING = "range_forming"
    RANGE_ESTABLISHED = "range_established"
    RANGE_HIGH_TOUCH = "range_high_touch"
    RANGE_LOW_TOUCH = "range_low_touch"
    MEAN_REVERSION_SETUP = "mean_reversion_setup"
    MEAN_REVERSION_TRIGGERED = "mean_reversion_triggered"
    MEAN_REVERSION_IN_PROGRESS = "mean_reversion_in_progress"
    MID_RANGE = "mid_range"
    TARGET_ZONE_APPROACHING = "target_zone_approaching"
    RANGE_FADE = "range_fade"
    RANGE_EXPANSION_ATTEMPT = "range_expansion_attempt"
    RANGE_BROKEN_UPSIDE = "range_broken_upside"
    RANGE_BROKEN_DOWNSIDE = "range_broken_downside"
    RANGE_TO_TREND = "range_to_trend"
    FAILED_MEAN_REVERSION = "failed_mean_reversion"
    RANGE_EXHAUSTION = "range_exhaustion"
    NO_TRADE = "no_trade"
    
    # Legacy / Compatibility
    TREND = "trend" 
    BREAKOUT = "breakout"
    TREND_IGNITION = "trend_ignition"
    TREND_EXHAUSTION = "trend_exhaustion"
    TREND_REVERSAL = "trend_reversal"

class StrategyFamily(Enum):
    TREND = "trend"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    MEAN_REVERSION = "mean_reversion"
    RANGE = "range"
    GAP = "gap"
    VOLATILITY = "volatility"

class StrategyPhase(Enum):
    # Lifecycle Phases
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    MANAGEMENT = "management"
    INVALIDATION = "invalidation"
    EXIT = "exit"

    # Setup Details
    SETUP_DETECTED = "setup_detected"
    SETUP_VALIDATED = "setup_validated"
    ENTRY_ARMED = "entry_armed"
    ENTRY_TRIGGERED = "entry_triggered"
    
    # Position States
    POSITION_OPEN = "position_open"
    CONTINUATION = "continuation"
    PARTIAL_EXIT = "partial_exit"
    TRAILING = "trailing"
    LATE_STAGE = "late_stage"
    
    # Termination
    EXIT_TRIGGERED = "exit_triggered"
    FAILURE = "failure"
    CLOSED = "closed"
    
    # Legacy
    PRE_CONDITION = "pre_condition"

@dataclass(frozen=True)
class TradeIdea:
    symbol: str
    asset_class: str
    timeframe: str
    strategy_name: str
    strategy_family: StrategyFamily
    strategy_subtype: str
    direction: Literal["long", "short"]
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence_score: float
    regime_tag: RegimeType
    lifecycle_phase: StrategyPhase
    invalidation_price: float
    holding_period_hint: str # e.g. "intraday", "swing"
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyStats:
    family: StrategyFamily
    name: str
    asset_class: str
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    expectancy: float = 0.0
    avg_r_multiple: float = 0.0
    total_trades: int = 0
