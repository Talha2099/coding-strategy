from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Literal, Any

class RegimeType(Enum):
    # Trend States
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    EARLY_TREND = "early_trend"
    MID_TREND = "mid_trend"
    LATE_TREND = "late_trend"
    PULLBACK_IN_TREND = "pullback_in_trend"
    
    # Other States
    RANGE = "range"
    BREAKOUT_PREP = "breakout_prep"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE_UNSTABLE = "volatile_unstable"
    REVERSAL_RISK = "reversal_risk"
    GAP_DRIVEN = "gap_driven"
    
    # Breakout Lifecycle
    BREAKOUT_ACTIVE = "breakout_active"
    POST_BREAKOUT_CONTINUATION = "post_breakout_continuation"
    FALSE_BREAKOUT_RISK = "false_breakout_risk"
    
    # Generic (for backward compatibility if needed)
    TREND = "trend" 
    BREAKOUT = "breakout"
    PULLBACK_CONTINUATION = "pullback_continuation"
    TREND_STABLE = "trend_stable"
    TREND_IGNITION = "trend_ignition"
    TREND_EXHAUSTION = "trend_exhaustion"
    TREND_REVERSAL = "trend_reversal"
    PRE_TREND = "pre_trend"

class StrategyFamily(Enum):
    TREND = "trend"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    MEAN_REVERSION = "mean_reversion"
    RANGE = "range"
    GAP = "gap"
    VOLATILITY = "volatility"

class StrategyPhase(Enum):
    # Setup States
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
    
    # Termination States
    EXIT_TRIGGERED = "exit_triggered"
    INVALIDATED = "invalidated"
    FAILURE = "failure"
    CLOSED = "closed"
    
    # Backward compatibility mappings (optional, but keep basic ones)
    PRE_CONDITION = "pre_condition"
    ACTIVE = "active"
    EXHAUSTION = "exhaustion"

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
