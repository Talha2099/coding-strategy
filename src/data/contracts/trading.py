from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Dict, Optional


@dataclass(frozen=True)
class TradeCandidate:
    id: str
    symbol: str
    direction: Literal["long", "short"]
    entry_zone: float
    stop_loss: float
    take_profit: float
    scenario: str
    timestamp: datetime

@dataclass(frozen=True)
class ScoredTrade:
    candidate: TradeCandidate
    probability: float
    expected_return: float
    risk_score: float
    features: Dict[str, float]

@dataclass(frozen=True)
class ExecutionOrder:
    id: str
    symbol: str
    side: str
    type: Literal["market", "limit"]
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
