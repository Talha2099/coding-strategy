from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict
from datetime import datetime

class EventType(Enum):
    TICK = "tick"
    ORDERBOOK = "orderbook"
    CANDLE = "candle"
    CANDIDATE = "candidate"
    ORDER = "order"
    FILL = "fill"

@dataclass(frozen=True)
class Event:
    type: EventType
    timestamp: datetime
    data: Any
    metadata: Dict[str, Any] = None
