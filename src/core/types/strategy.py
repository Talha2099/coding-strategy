from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Literal

class RegimeType(Enum):
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    RANGING = "ranging"
    MEAN_REVERSION = "mean_reversion"
    GAP = "gap"
    VOLATILE_UNSTABLE = "volatile_unstable"

class StrategyFamily(Enum):
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
