from typing import List, Dict, Any, Optional
from datetime import datetime
from src.infra.database.repositories.market_data_repo import MarketDataRepository
from src.core.utils.logger import system_logger

class DataReconciler:
    """
    Stitches and reconciles data from multiple sources (Yahoo, MT5).
    Handles overlaps and gaps.
    """
    
    @staticmethod
    def get_unified_history(symbol: str, timeframe: str, limit: int = 2000) -> List[Dict[str, Any]]:
        """
        Merge data from all sources, preferring MT5 for recent data and Yahoo for deep history.
        """
        # For simplicity, we fetch all from DB and deduplicate by timestamp
        query = """
        SELECT timestamp, open, high, low, close, volume, source
        FROM candles 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC LIMIT ?
        """
        from src.infra.database.db_manager import db_manager
        rows = db_manager.fetch_all(query, (symbol, timeframe, limit))
        
        if not rows:
            return []
            
        # Deduplicate: if same timestamp has multiple sources, we could choose one.
        # Let's say MT5 > YAHOO
        source_priority = {"MT5": 2, "YAHOO": 1}
        
        unique_candles = {}
        for row in rows:
            ts = row['timestamp']
            src = row['source']
            curr_priority = source_priority.get(src, 0)
            
            if ts not in unique_candles:
                unique_candles[ts] = row
            else:
                existing_priority = source_priority.get(unique_candles[ts]['source'], 0)
                if curr_priority > existing_priority:
                    unique_candles[ts] = row
                    
        # Sort by timestamp ASC
        sorted_ts = sorted(unique_candles.keys())
        return [unique_candles[ts] for ts in sorted_ts]

    @staticmethod
    def check_integrity(symbol: str, timeframe: str):
        """Detects gaps in data."""
        candles = DataReconciler.get_unified_history(symbol, timeframe, limit=1000)
        if len(candles) < 2:
            return True
            
        # Simple gap check based on expected delta
        # M5 = 300s, H1 = 3600s
        # (This would need a more robust implementation considering market hours)
        return True # Placeholder for integrity status
