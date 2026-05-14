from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Literal

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

@dataclass(frozen=True)
class TradeIdea:
    symbol: str
    asset_class: str
    strategy_name: str
    strategy_family: StrategyFamily
    direction: Literal["long", "short"]
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence_score: float
    regime_tag: RegimeType
    holding_period_hint: str # e.g. "intraday", "swing"
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

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
