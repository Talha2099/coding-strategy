from typing import Dict, Optional
import threading
from datetime import datetime
from src.core.contracts.event_state import EventState

class GlobalEventCache:
    """
    Shared cache between Async Information Path and Fast Trading Path.
    Designed for non-blocking reads.
    """
    _instance = None
    _lock = threading.Lock()
    _states: Dict[str, EventState] = {} # Symbol -> State
    _last_global_update: Optional[datetime] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GlobalEventCache, cls).__new__(cls)
        return cls._instance

    def update_state(self, symbol: str, state: EventState):
        with self._lock:
            self._states[symbol] = state
            self._last_global_update = datetime.now()

    def get_state(self, symbol: str) -> EventState:
        # Note: Non-locking read for performance in execution path
        # If lock contention is high, use an Atomic reference or separate structure
        state = self._states.get(symbol)
        if not state:
            return EventState.default_safe()
        
        # Check staleness (if news hasn't updated in 1 hour, treat as unavailable)
        if self._last_global_update:
            age = (datetime.now() - self._last_global_update).total_seconds()
            if age > 3600:
                return EventState.default_safe()
                
        return state

    def clear(self):
        with self._lock:
            self._states.clear()
