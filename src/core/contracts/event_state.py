from typing import Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class EventType(Enum):
    MACRO = "macro"         # CPI, FOMC, etc.
    EARNINGS = "earnings"
    CORPORATE = "corporate" # Dividends, Splits
    HEADLINE = "headline"   # Breaking news
    UNSCHEDULED = "unscheduled"

class EventImportance(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class EventState:
    """
    PHASE 13: Event State Model for Async Information Path.
    Used by the risk engine to modify exposure around known windows.
    """
    event_available: bool = False
    event_type: Optional[EventType] = None
    event_importance: EventImportance = EventImportance.LOW
    event_time: Optional[datetime] = None
    time_to_event_minutes: Optional[float] = None
    time_since_event_minutes: Optional[float] = None
    event_confidence: float = 0.0
    event_risk_level: float = 0.0 # 0.0 (Safe) to 1.0 (Extreme)
    news_latency_ms: float = 0.0
    source_health: float = 1.0 # 0.0 (Failed) to 1.0 (Healthy)
    trade_blocked: bool = False
    risk_multiplier: float = 1.0
    
    @classmethod
    def default_safe(cls):
        return cls(event_available=False, event_risk_level=0.0, risk_multiplier=1.0)
