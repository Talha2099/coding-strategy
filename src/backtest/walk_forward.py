import uuid
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import BacktestMetrics
from src.infra.database.repositories.backtest_repo import BacktestRepository
from src.infra.database.db_manager import db_manager
from src.core.utils.logger import system_logger
import json

class WalkForwardEngine:
    """
    STAGE M: Walk-Forward Testing.
    Implements rolling window out-of-sample testing.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.run_id = str(uuid.uuid4())
        self.train_size = config.get('train_size_bars', 1000)
        self.test_size = config.get('test_size_bars', 200)

    def run(self, symbol: str, timeframe: str, candles: List[Any], strategy_logic: Any) -> Dict[str, Any]:
        system_logger.info(f"Starting Walk-Forward Run: {self.run_id}")
        
        total_bars = len(candles)
        current_idx = self.train_size
        window_index = 0
        window_results = []
        all_oos_trades = []

        # Persistence of run meta
        self._save_run_meta(symbol, candles)

        while current_idx + self.test_size <= total_bars:
            train_candles = candles[current_idx - self.train_size : current_idx]
            test_candles = candles[current_idx : current_idx + self.test_size]
            
            # 1. Train / Optimize phase (Placeholder for actual optimization)
            # In a real system, you'd call a parameter optimizer here
            best_params = {"placeholder": True}
            train_metric = 0.5 # Dummy
            
            # 2. Test / OOS phase
            engine = BacktestEngine(
                initial_capital=self.config.get('initial_capital', 100000.0),
                commission=self.config.get('commission', 0.0001),
                slippage=self.config.get('slippage', 0.0001)
            )
            
            oos_trades = engine.run(symbol, timeframe, test_candles, strategy_logic)
            all_oos_trades.extend(oos_trades)
            
            # Calculate OOS window metrics
            oos_summary = BacktestMetrics.calculate_metrics(oos_trades, engine.initial_capital)
            
            window_data = {
                "run_id": self.run_id,
                "window_index": window_index,
                "train_start": train_candles[0].ts,
                "train_end": train_candles[-1].ts,
                "test_start": test_candles[0].ts,
                "test_end": test_candles[-1].ts,
                "train_metric": train_metric,
                "test_metric": oos_summary['sharpe_ratio'],
                "params": best_params
            }
            
            self._save_window(window_data)
            window_results.append(window_data)
            
            current_idx += self.test_size
            window_index += 1

        # Final OOS Summary
        total_oos_summary = BacktestMetrics.calculate_metrics(all_oos_trades, self.config.get('initial_capital', 100000.0))
        
        # Update run with final metrics
        self._update_run_final(total_oos_summary)
        
        return {
            "run_id": self.run_id,
            "summary": total_oos_summary,
            "windows": window_results
        }

    def _save_run_meta(self, symbol: str, candles: List[Any]):
        query = """
        INSERT INTO walk_forward_runs 
        (run_id, symbol, config_json, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            self.run_id, symbol, json.dumps(self.config),
            candles[0].ts if candles else None,
            candles[-1].ts if candles else None
        ))

    def _save_window(self, data: Dict[str, Any]):
        query = """
        INSERT INTO walk_forward_windows 
        (run_id, window_index, train_start, train_end, test_start, test_end, train_metric, test_metric, params_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_manager.execute(query, (
            data['run_id'], data['window_index'], data['train_start'], data['train_end'],
            data['test_start'], data['test_end'], data['train_metric'], data['test_metric'],
            json.dumps(data['params'])
        ))

    def _update_run_final(self, summary: Dict[str, Any]):
        query = "UPDATE walk_forward_runs SET oos_sharpe = ?, oos_pnl = ? WHERE run_id = ?"
        db_manager.execute(query, (summary['sharpe_ratio'], summary['net_pnl'], self.run_id))
