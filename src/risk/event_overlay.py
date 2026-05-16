from typing import Optional, Tuple
from src.core.contracts.event_state import EventState, EventImportance
from src.data.news.cache import GlobalEventCache
from src.core.contracts.instrument_registry import InstrumentRegistry

class EventRiskOverlay:
    """
    PHASE 13: Event Risk Overlay.
    Integrates the Information Path into the Risk Engine.
    """
    def __init__(self):
        self.cache = GlobalEventCache()

    def get_event_adjustment(self, symbol: str) -> Tuple[float, Optional[str]]:
        """
        Returns (risk_multiplier, reason)
        If news is unavailable or stale, returns (1.0, None) -> DEFAULT TO TECHNICALS.
        """
        state = self.cache.get_state(symbol)
        
        if not state.event_available:
            return 1.0, None

        # 1. Check if trade is blocked entirely (Hard Block)
        if state.trade_blocked:
            return 0.0, "EVENT_HARD_BLOCK"

        # 2. Importance-based adjustments
        if state.event_importance == EventImportance.CRITICAL:
            # Check proximity
            if state.time_to_event_minutes and state.time_to_event_minutes < 15:
                return 0.0, "CRITICAL_EVENT_PROXIMITY"
            if state.time_since_event_minutes and state.time_since_event_minutes < 15:
                return 0.2, "POST_CRITICAL_EVENT_COOLING"
        
        # 3. Use the calculated risk multiplier from the sidecar
        # This keeps the logic localized in the async path for complex processing (e.g. NLP)
        return state.risk_multiplier, f"EVENT_{state.event_type.value if state.event_type else 'UNKNOWN'}"

    def should_widen_stops(self, symbol: str) -> bool:
        """
        Indices and Gold often need wider stops during high-impact news.
        """
        state = self.cache.get_state(symbol)
        spec = InstrumentRegistry.get_spec(symbol)
        
        if not state.event_available:
            return False
            
        # Example: Increase stop distance if sensitivity is high and event is upcoming
        if spec.behavior.event_risk_sensitivity > 0.7:
            if state.event_importance in [EventImportance.HIGH, EventImportance.CRITICAL]:
                return True
                
        return False
