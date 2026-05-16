from typing import Dict, List, Optional
from datetime import datetime
from src.core.types.trading import Tick, Candle
import pandas as pd
import numpy as np

class TickCleaner:
    """
    PHASE 13: Fast-Path Tick Processing.
    Filters outliers, calculates micro-spreads, and aggregates into candles.
    """
    def __init__(self, symbol: str, timeframe_seconds: int = 60):
        self.symbol = symbol
        self.timeframe_seconds = timeframe_seconds
        self.current_candle: Optional[Dict] = None
        self.last_clean_tick: Optional[Tick] = None
        
    def process_tick(self, tick: Tick) -> Tuple[bool, Optional[Candle]]:
        """
        Returns (is_new_candle, candle_if_closed)
        """
        # 1. Outlier Removal (Price Spike Check)
        if self.last_clean_tick:
            pct_change = abs(tick.last - self.last_clean_tick.last) / self.last_clean_tick.last
            if pct_change > 0.02: # 2% spike in one tick is likely an MT5 error/gap
                return False, None
        
        self.last_clean_tick = tick
        
        # 2. Candle Aggregation
        tick_ts = tick.ts
        candle_ts = tick_ts.replace(second=0, microsecond=0) # Simple 1m floor
        
        if not self.current_candle or candle_ts > self.current_candle["ts"]:
            closed_candle = None
            if self.current_candle:
                closed_candle = Candle(
                    symbol=self.symbol,
                    ts=self.current_candle["ts"],
                    open=self.current_candle["open"],
                    high=self.current_candle["high"],
                    low=self.current_candle["low"],
                    close=self.current_candle["close"],
                    volume=self.current_candle["volume"]
                )
            
            self.current_candle = {
                "ts": candle_ts,
                "open": tick.last,
                "high": tick.last,
                "low": tick.last,
                "close": tick.last,
                "volume": tick.volume
            }
            return True, closed_candle
            
        # Update current candle
        self.current_candle["high"] = max(self.current_candle["high"], tick.last)
        self.current_candle["low"] = min(self.current_candle["low"], tick.last)
        self.current_candle["close"] = tick.last
        self.current_candle["volume"] += tick.volume
        
        return False, None
from typing import Tuple
