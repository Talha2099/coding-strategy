from pydantic import BaseModel
from typing import List, Optional

class BehaviorProfile(BaseModel):
    name: str
    session_sensitivity: float = 1.0 # 1.0 is neutral
    volatility_window_expansion: bool = False
    stop_adjustment_multiplier: float = 1.0
    gap_continuation_probability: float = 0.5
    gap_fill_probability: float = 0.5
    overnight_cost_sensitivity: float = 1.0
    auction_sensitivity: bool = False
    earnings_sensitivity: bool = False
    macro_session_impact: bool = False

GOLD_PROFILE = BehaviorProfile(
    name="Gold",
    session_sensitivity=1.5, # High sensitivity to session starts
    volatility_window_expansion=True, # Active during London/NY overlaps
    stop_adjustment_multiplier=1.2, # Wider stops for gold volatility
    overnight_cost_sensitivity=1.2, # Significant swap impact
    macro_session_impact=True
)

INDEX_PROFILE = BehaviorProfile(
    name="Index",
    session_sensitivity=2.0, # Very high at open
    auction_sensitivity=True, # Opening auctions matter
    gap_continuation_probability=0.65, # Indices often trend after gaps
    gap_fill_probability=0.35,
    macro_session_impact=True
)

STOCK_PROFILE = BehaviorProfile(
    name="Stock",
    gap_fill_probability=0.6, # Stocks often fill gaps
    earnings_sensitivity=True,
    auction_sensitivity=True,
    overnight_cost_sensitivity=0.8
)
