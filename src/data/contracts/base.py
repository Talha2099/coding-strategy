from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Literal, Dict, Optional

@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(frozen=True)
class Tick:
    ts: datetime
    price: float
    size: float
    side: Literal["buy", "sell"]

@dataclass(frozen=True)
class OrderBookSnapshot:
    ts: datetime
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]

@dataclass(frozen=True)
class MicrostructureFeatures:
    spread: float
    mid_price: float
    imbalance: float
    order_flow_imbalance: float
    realized_volatility: float
    trade_intensity: float
