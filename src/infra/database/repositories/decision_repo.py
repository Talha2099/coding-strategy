import json
from typing import Dict, Any, Optional
from src.infra.database.db_manager import db_manager

class DecisionRepository:
    """
    STAGE N: Risk and Decision Logs.
    Persists granular logs of every step in the trading lifecycle.
    """
    
    @staticmethod
    def log_risk_decision(data: Dict[str, Any]):
        query = """
        INSERT INTO risk_decisions 
        (candidate_id, risk_score, position_size, stop_distance, take_profit_distance, 
         volatility_adj, regime_adj, is_approved, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            data['candidate_id'], data.get('risk_score'), data.get('position_size'),
            data.get('stop_distance'), data.get('take_profit_distance'),
            data.get('volatility_adj', 1.0), data.get('regime_adj', 1.0),
            1 if data.get('is_approved', True) else 0,
            data.get('reason')
        ))

    @staticmethod
    def log_event(event_type: str, ref_id: str, market_snapshot: Dict[str, Any], decision: Dict[str, Any], outcome: Optional[Dict[str, Any]] = None):
        """
        Stores a structured decision log for research and audit.
        """
        query = """
        INSERT INTO decision_logs (event_type, ref_id, market_snapshot_json, decision_json, outcome_json)
        VALUES (?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            event_type, 
            ref_id, 
            json.dumps(market_snapshot), 
            json.dumps(decision), 
            json.dumps(outcome) if outcome else None
        ))

    @staticmethod
    def get_logs_for_candidate(candidate_id: str):
        query = "SELECT * FROM decision_logs WHERE ref_id = ?"
        return db_manager.fetch_all(query, (candidate_id,))
