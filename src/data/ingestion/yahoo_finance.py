import yfinance as yf
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.core.utils.logger import system_logger
from src.infra.database.repositories.market_data_repo import MarketDataRepository

class YahooFinanceIngestor:
    """
    Fetches historical OHLCV data from Yahoo Finance.
    """
    
    @staticmethod
    def fetch_historical(symbol: str, timeframe: str, start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches and normalizes Yahoo Finance data.
        timeframe mapping: M1 -> 1m, M5 -> 5m, M15 -> 15m, H1 -> 1h, D1 -> 1d
        """
        tf_map = {
            "M1": "1m",
            "M5": "5m",
            "M15": "15m",
            "H1": "1h",
            "D1": "1d"
        }
        interval = tf_map.get(timeframe, "1d")
        
        system_logger.info(f"Fetching {symbol} ({timeframe}) from Yahoo Finance: {start_date} to {end_date or 'now'}")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                system_logger.warning(f"No data returned for {symbol} from Yahoo Finance.")
                return []
                
            # Normalize column names and format
            df = df.reset_index()
            df = df.rename(columns={
                "Datetime": "timestamp",
                "Date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            # Convert timestamp to ISO format string
            df['timestamp'] = df['timestamp'].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
            
            candles = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
            
            # Persist to database
            MarketDataRepository.save_candles(symbol, timeframe, "YAHOO", candles)
            
            system_logger.info(f"Successfully ingested {len(candles)} bars for {symbol}.")
            return candles
            
        except Exception as e:
            system_logger.error(f"Failed to fetch data from Yahoo Finance for {symbol}: {e}")
            return []

    @staticmethod
    def sync_latest(symbol: str, timeframe: str):
        """Syncs data starting from the last stored timestamp."""
        last_ts = MarketDataRepository.get_last_timestamp(symbol, timeframe, "YAHOO")
        if not last_ts:
            # If no data, fetch last 30 days by default
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            # Start from the last timestamp found
            start_date = last_ts.split('T')[0]
            
        return YahooFinanceIngestor.fetch_historical(symbol, timeframe, start_date)
