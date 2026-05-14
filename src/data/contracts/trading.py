from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Dict, Optional, Any, List


@dataclass(frozen=True)
class TradeCandidate:
    id: str
    symbol: str
    asset_class: str
    direction: Literal["long", "short"]
    entry_zone_id: str
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_family: str
    strategy_name: str
    regime_at_entry: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    direction: Literal["long", "short"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    features: Dict[str, float]
    strategy_name: str
    timestamp: datetime

@dataclass(frozen=True)
class RiskDecision:
    signal_id: str
    approved: bool
    size: float
    reason: str
    max_drawdown_impact: float
    timestamp: datetime

@dataclass(frozen=True)
class Action:
    type: Literal["enter", "exit", "scale_in", "scale_out", "update_stop", "cancel"]
    symbol: str
    side: str
    size: float
    price: Optional[float]
    order_type: str = "market"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class RegimeState:
    symbol: str
    regime_type: str
    probabilities: Dict[str, float]
    volatility: float
    trend_strength: float
    timestamp: datetime

@dataclass(frozen=True)
class ExecutionReport:
    action_id: str
    order_id: str
    status: Literal["filled", "rejected", "canceled", "partial"]
    fill_price: Optional[float]
    fill_size: float
    slippage: float
    commission: float
    venue: str
    timestamp: datetime

@dataclass(frozen=True)
class TradeLogEvent:
    event_id: str
    trade_id: str
    event_type: str # "entry", "stop_moved", "partial_exit", "close", "regime_shift"
    message: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ScoredTrade:
    candidate: TradeCandidate
    probability: float
    expected_return: float
    risk_score: float
    features: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ExecutionOrder:
    id: str
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "limit", "stop", "stop_limit"]
    price: Optional[float]
    size: float
    timestamp: datetime

@dataclass(frozen=True)
class FillResult:
    order_id: str
    fill_price: float
    fill_size: float
    slippage: float
    commission: float
    timestamp: datetime

@dataclass
class Position:
    id: str
    symbol: str
    asset_class: str
    size: float 
    entry_price: float
    avg_price: float
    stop_loss: float
    take_profit: float
    entry_ts: datetime
    strategy_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
