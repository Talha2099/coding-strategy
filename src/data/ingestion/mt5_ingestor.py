try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.core.utils.logger import system_logger
from src.infra.database.repositories.market_data_repo import MarketDataRepository

class MT5Ingestor:
    """
    Fetches live and historical data from MetaTrader 5.
    Requires MT5 terminal to be running on the machine.
    """
    
    def __init__(self):
        self.connected = False
        if mt5:
            self._connect()

    def _connect(self):
        if not mt5.initialize():
            system_logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
        self.connected = True
        system_logger.info("Connected to MT5 terminal.")
        return True

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 100) -> List[Dict[str, Any]]:
        if not self.connected and not self._connect():
            return []
            
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "D1": mt5.TIMEFRAME_D1
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_D1)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        if rates is None:
            system_logger.error(f"Failed to fetch rates for {symbol}: {mt5.last_error()}")
            return []
            
        candles = []
        for rate in rates:
            candles.append({
                "timestamp": datetime.fromtimestamp(rate['time']).isoformat(),
                "open": float(rate['open']),
                "high": float(rate['high']),
                "low": float(rate['low']),
                "close": float(rate['close']),
                "volume": float(rate['tick_volume']) # Use tick volume for FX
            })
            
        # Persist
        MarketDataRepository.save_candles(symbol, timeframe, "MT5", candles)
        return candles

    def fetch_ticks(self, symbol: str, count: int = 10) -> List[Dict[str, Any]]:
        if not self.connected and not self._connect():
            return []
            
        mt5_ticks = mt5.copy_ticks_from_pos(symbol, 0, count, mt5.COPY_TICKS_ALL)
        if mt5_ticks is None:
            return []
            
        ticks = []
        for t in mt5_ticks:
            ticks.append({
                "symbol": symbol,
                "timestamp": datetime.fromtimestamp(t['time']).isoformat(),
                "bid": float(t['bid']),
                "ask": float(t['ask']),
                "last": float(t['last']),
                "volume": float(t['volume']),
                "source": "MT5"
            })
        return ticks

    def __del__(self):
        if self.connected and mt5:
            mt5.shutdown()
