import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from src.infra.database.db_manager import db_manager

class AttributionReportEngine:
    """
    STAGE O: Reporting and Attribution.
    Analyzes trade history to identify performance drivers.
    """
    
    @staticmethod
    def generate_full_report(backtest_id: str) -> Dict[str, Any]:
        """Generates a complete attribution report for a given backtest."""
        trades = AttributionReportEngine._get_trades(backtest_id)
        if not trades:
            return {"status": "NO_TRADES"}

        df = pd.DataFrame(trades)
        
        # 1. Regime Attribution
        regime_attr = df.groupby('regime').agg({
            'pnl': 'sum',
            'pos_id': 'count'
        }).rename(columns={'pos_id': 'trade_count'}).to_dict('index')

        # 2. Strategy Attribution
        strategy_attr = df.groupby('strategy').agg({
            'pnl': 'sum',
            'pos_id': 'count'
        }).rename(columns={'pos_id': 'trade_count'}).to_dict('index')

        # 3. Session Attribution (Placeholder logic, needs session mapping in trades)
        session_attr = {} 

        # 4. Long vs Short
        df['direction'] = df['pnl'].apply(lambda x: "Profit" if x > 0 else "Loss") # Dummy until direction added to history
        side_attr = df.groupby('regime')['pnl'].sum().to_dict()

        return {
            "backtest_id": backtest_id,
            "total_pnl": float(df['pnl'].sum()),
            "win_rate": float((df['pnl'] > 0).mean()),
            "by_regime": regime_attr,
            "by_strategy": strategy_attr,
            "trade_count": len(df)
        }

    @staticmethod
    def _get_trades(backtest_id: str) -> List[Dict[str, Any]]:
        # This assumes we have a link between backtests and trades in DB
        # For now, we query decision_logs or fills to reconstruct
        query = """
        SELECT ref_id as pos_id, outcome_json 
        FROM decision_logs 
        WHERE event_type = 'EXIT' 
        """
        rows = db_manager.fetch_all(query)
        trades = []
        for r in rows:
            outcome = eval(r['outcome_json']) if r['outcome_json'] else {}
            trades.append({
                "pos_id": r['pos_id'],
                "pnl": outcome.get('pnl', 0.0),
                "regime": "UNKNOWN", # Need more join logic for real regime
                "strategy": "ALPHA"
            })
        return trades
