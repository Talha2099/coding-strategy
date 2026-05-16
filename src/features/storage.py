import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from src.features.versioning import FeatureVersioning
from src.infra.database.repositories.feature_repo import FeatureRepository

class FeatureStorage:
    """
    STAGE K: Storage and Versioning.
    Persists feature vectors for replay, attribution, and research.
    """
    def __init__(self, base_path: str = "data/features"):
        self.base_path = base_path
        self.metadata = FeatureVersioning.get_metadata()
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)

    def store_vector(self, 
                     symbol: str, 
                     timestamp: str, 
                     vector: Dict[str, float], 
                     timeframe: str = "1m",
                     context: Optional[Dict[str, Any]] = None):
        """Stores a scalar feature vector with full context in both DB and File."""
        # 1. Database Persistence
        FeatureRepository.save_feature_snapshot(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            version=self.metadata["version"],
            features=vector
        )

        # 2. File-system Persistence (JSONL)
        payload = {
            "symbol": symbol,
            "timestamp": timestamp,
            "version": self.metadata["version"],
            "features": vector,
            "context": context or {},
            "stored_at": datetime.utcnow().isoformat()
        }
        
        # In a real system, this might go to BigQuery, Snowflake, or a TimescaleDB
        # For this implementation, we log the intent and provide a file-system mock
        # system_logger.log_event("FEATURE_STORED", {"symbol": symbol, "ts": timestamp})
        
        # Path: data/features/{symbol}/{version}/{date}.jsonl
        date_str = timestamp.split('T')[0]
        dir_path = os.path.join(self.base_path, symbol, self.metadata["version"])
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{date_str}.jsonl")
        with open(file_path, "a") as f:
            f.write(json.dumps(payload) + "\n")

    def load_vector(self, symbol: str, timestamp: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves a stored feature vector for replay."""
        v = version or self.metadata["version"]
        date_str = timestamp.split('T')[0]
        file_path = os.path.join(self.base_path, symbol, v, f"{date_str}.jsonl")
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r") as f:
            for line in f:
                data = json.loads(line)
                if data["timestamp"] == timestamp:
                    return data
        return None
