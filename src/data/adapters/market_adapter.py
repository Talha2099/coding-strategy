import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from src.core.types.trading import Candle, Tick

class DataAdapter:
    """
    Bridge between historical OHLC data (e.g. yfinance) and the event-driven system.
    Handles the 'Skip OFI' logic for backtesting when L2/Tick data is missing.
    """
    @staticmethod
    def candles_to_ticks(candles: List[Candle]) -> List[Tick]:
        """
        Converts OHLC candles to synthetic ticks if actual ticks are missing.
        Ensures the pipeline doesn't break when OFI is unavailable.
        """
        all_ticks = []
        for c in candles:
            # 4 synthetic ticks: O, H, L, C
            all_ticks.extend([
                Tick(c.ts, c.open, c.volume/4, "buy"),
                Tick(c.ts, c.high, c.volume/4, "buy"),
                Tick(c.ts, c.low, c.volume/4, "sell"),
                Tick(c.ts, c.close, c.volume/4, "sell"),
            ])
        return all_ticks

    @staticmethod
    def get_ofi_availability(data_source: str) -> bool:
        """
        Checks if the current data source supports Order Flow Imbalance.
        """
        sources_with_ofi = ["binance_ws", "oanda_v20", "interactive_brokers"]
        return data_source in sources_with_ofi
