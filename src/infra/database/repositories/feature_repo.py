import json
from typing import Dict, Any, List, Optional
from src.infra.database.db_manager import db_manager

class FeatureRepository:
    """
    Handles persistence and retrieval of feature snapshots and regime states.
    """
    
    @staticmethod
    def save_feature_snapshot(symbol: str, timeframe: str, timestamp: str, version: str, features: Dict[str, Any]):
        query = """
        INSERT INTO feature_snapshots 
        (symbol, timeframe, timestamp, version, features_json)
        VALUES (?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            symbol, timeframe, timestamp, version, json.dumps(features)
        ))

    @staticmethod
    def save_regime_state(symbol: str, timeframe: str, timestamp: str, regime: str, score: float = 0.0, probabilities: Optional[Dict[str, float]] = None):
        query = """
        INSERT INTO regime_states 
        (symbol, timeframe, timestamp, current_regime, regime_score, probabilities_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            symbol, timeframe, timestamp, regime, score, json.dumps(probabilities or {})
        ))

    @staticmethod
    def get_latest_features(symbol: str, timeframe: str, limit: int = 100) -> List[Dict[str, Any]]:
        query = """
        SELECT * FROM feature_snapshots 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC LIMIT ?
        """
        return db_manager.fetch_all(query, (symbol, timeframe, limit))
