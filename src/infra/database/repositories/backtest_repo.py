from typing import List, Dict, Any, Optional
import json
from src.infra.database.db_manager import db_manager

class BacktestRepository:
    """
    Handles persistence of backtest runs and summary statistics.
    """
    
    @staticmethod
    def save_backtest_run(backtest_data: Dict[str, Any]):
        query = """
        INSERT INTO backtests 
        (backtest_id, name, strategy_config_json, start_date, end_date, initial_capital, final_equity, total_trades, sharpe_ratio, max_drawdown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            backtest_data['backtest_id'], backtest_data.get('name'), 
            json.dumps(backtest_data.get('config', {})),
            backtest_data.get('start_date'), backtest_data.get('end_date'),
            backtest_data.get('initial_capital'), backtest_data.get('final_equity'),
            backtest_data.get('total_trades'), backtest_data.get('sharpe_ratio'),
            backtest_data.get('max_drawdown')
        ))

    @staticmethod
    def get_backtest_summary(backtest_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM backtests WHERE backtest_id = ?"
        return db_manager.fetch_one(query, (backtest_id,))
