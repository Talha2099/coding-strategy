from typing import List, Dict, Any, Optional
from datetime import datetime
from src.infra.database.db_manager import db_manager

class MarketDataRepository:
    """
    Handles persistence and retrieval of candles, ticks, and instruments.
    """
    
    @staticmethod
    def save_instrument(spec: Dict[str, Any]):
        query = """
        INSERT OR REPLACE INTO instruments 
        (symbol, name, asset_class, archetype, point_value, tick_size, contract_size, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            spec['symbol'], spec.get('name'), spec.get('asset_class'), spec.get('archetype'),
            spec.get('point_value', 1.0), spec.get('tick_size', 0.01), 
            spec.get('contract_size', 1.0), spec.get('currency', 'USD')
        ))

    @staticmethod
    def save_candles(symbol: str, timeframe: str, source: str, candles: List[Dict[str, Any]]):
        """Batch insert candles."""
        query = """
        INSERT OR IGNORE INTO candles 
        (symbol, timeframe, timestamp, open, high, low, close, volume, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            (symbol, timeframe, c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume'], source)
            for c in candles
        ]
        db_manager.execute_batch(query, params)

    @staticmethod
    def get_candles(symbol: str, timeframe: str, limit: int = 1000, start_date: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
        SELECT * FROM candles 
        WHERE symbol = ? AND timeframe = ?
        """
        params = [symbol, timeframe]
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
            
        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)
        
        return db_manager.fetch_all(query, tuple(params))

    @staticmethod
    def get_last_timestamp(symbol: str, timeframe: str, source: str) -> Optional[str]:
        query = "SELECT MAX(timestamp) as ts FROM candles WHERE symbol = ? AND timeframe = ? AND source = ?"
        res = db_manager.fetch_one(query, (symbol, timeframe, source))
        return res['ts'] if res else None
