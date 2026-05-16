from typing import Dict, List, Optional, Callable
import time
from datetime import datetime
from dataclasses import dataclass
from src.core.types.trading import Tick, Candle
from src.core.utils.logger import system_logger

@dataclass
class MT5Tick:
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    time_msc: int # Millisecond timestamp

class MT5Adapter:
    """
    PHASE 13: MT5 Fast Path Adapter.
    Interface for MetaTrader 5 Terminal via Python API.
    Used for the low-latency execution channel.
    """
    def __init__(self):
        self.connected = False
        self.tick_callbacks: List[Callable[[Tick], None]] = []

    def connect(self) -> bool:
        """Simulates connection to MT5 Terminal."""
        # In production: import MetaTrader5 as mt5; mt5.initialize()
        self.connected = True
        system_logger.log_event("MT5_CONNECTED", {"status": "SUCCESS"})
        return True

    def toggle_tick_stream(self, symbols: List[str], enabled: bool):
        """Simulates subscribing to symbols."""
        if enabled:
            system_logger.log_event("MT5_SUBSCRIPTION", {"symbols": symbols})

    def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        """Fast path poll for latest price."""
        # Mocking real-time return
        return Tick(
            symbol=symbol,
            bid=1.0750,
            ask=1.0751,
            last=1.07505,
            volume=10,
            ts=datetime.now()
        )

    def get_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        """Blocking call to get historical data for strategy warmup."""
        # mt5.copy_rates_from_pos(...)
        return []

    def disconnect(self):
        self.connected = False
        system_logger.log_event("MT5_DISCONNECTED", {})
