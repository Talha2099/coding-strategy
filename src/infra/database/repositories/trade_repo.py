from typing import List, Dict, Any, Optional
import json
from src.infra.database.db_manager import db_manager

class TradeRepository:
    """
    Handles persistence of trade candidates, orders, and fills.
    """
    
    @staticmethod
    def save_candidate(candidate: Dict[str, Any]):
        query = """
        INSERT INTO trade_candidates 
        (id, symbol, timestamp, strategy_name, direction, entry_price, stop_loss, take_profit, 
         risk_reward_ratio, validation_score, raw_signal_json, regime_at_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            candidate['id'], candidate['symbol'], candidate['timestamp'], candidate['strategy_name'],
            candidate['direction'], candidate.get('entry_price'), candidate.get('stop_loss'), 
            candidate.get('take_profit'), candidate.get('risk_reward_ratio'), 
            candidate.get('validation_score'), json.dumps(candidate.get('raw_signal_json', {})),
            candidate.get('regime_at_time'), candidate.get('status', 'PENDING')
        ))

    @staticmethod
    def update_candidate_status(candidate_id: str, status: str):
        query = "UPDATE trade_candidates SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        db_manager.execute(query, (status, candidate_id))

    @staticmethod
    def save_order(order: Dict[str, Any]):
        query = """
        INSERT INTO orders 
        (order_id, candidate_id, symbol, order_type, direction, quantity, price, stop_loss, take_profit, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            order['order_id'], order.get('candidate_id'), order['symbol'], order['order_type'],
            order['direction'], order['quantity'], order.get('price'), 
            order.get('stop_loss'), order.get('take_profit'), order.get('status', 'OPEN')
        ))

    @staticmethod
    def get_active_orders(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM orders WHERE status = 'OPEN'"
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        return db_manager.fetch_all(query, tuple(params))
