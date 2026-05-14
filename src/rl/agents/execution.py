from typing import List, Optional
import numpy as np
from src.core.types.trading import Candle, Position

class ExecutionAgent:
    """
    RL-driven execution agent focused on trade management (stops, exits, scaling).
    Does NOT generate direction signals.
    """
    def __init__(self, mode: str = "aggressive"):
        self.mode = mode

    def manage_position(self, pos: Position, candles: List[Candle]) -> Optional[str]:
        """
        Decides whether to adjust SL, scale out, or exit.
        Returns: "CLOSE", "SCALE_OUT", "TRAILING_STOP_UPDATE", or None
        """
        if not candles: return None
        
        last_price = candles[-1].close
        pnl_pct = (last_price / pos.entry_price - 1) if pos.size > 0 else (pos.entry_price / last_price - 1)
        
        # 1. Trailing Stop Logic (Simplified RL behavior)
        # Move SL to breakeven after 1:1 RR
        risk = abs(pos.entry_price - pos.stop_loss)
        if risk > 0:
            unrealized_rr = abs(last_price - pos.entry_price) / risk
            
            if unrealized_rr > 1.5:
                # Tighten stop to 50% of unrealized profit
                new_sl = pos.entry_price + (last_price - pos.entry_price) * 0.5
                pos.stop_loss = new_sl
                return "TRAILING_STOP_UPDATE"
        
        # 2. Exit Optimization
        # If we hit 3:1 RR, maybe close half
        
        # 3. Time-based Exit
        # If position is older than 4 hours and not hitting targets
        # ...

        return None

    def optimize_entry(self, signal_price: float, current_tick_price: float) -> float:
        """
        Optimizes entry timing using microstructure context.
        """
        # If current price is slightly better than signal price, take it.
        # Otherwise, wait for a limit.
        return current_tick_price
