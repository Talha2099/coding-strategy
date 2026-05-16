import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import BacktestMetrics
from src.infra.database.repositories.backtest_repo import BacktestRepository
from src.core.utils.logger import system_logger

class BacktestRunner:
    """
    Orchestrates backtest execution and persistence.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backtest_id = str(uuid.uuid4())
        self.engine = BacktestEngine(
            initial_capital=config.get('initial_capital', 100000.0),
            commission=config.get('commission', 0.0001),
            slippage=config.get('slippage', 0.0001)
        )

    def run(self, symbol: str, timeframe: str, candles: List[Any], strategy_logic: Any) -> Dict[str, Any]:
        system_logger.info(f"Starting Backtest: {self.backtest_id} for {symbol} ({timeframe})")
        
        # Execute
        trades = self.engine.run(symbol, timeframe, candles, strategy_logic)
        
        # Calculate Metrics
        summary = BacktestMetrics.calculate_metrics(trades, self.engine.initial_capital)
        
        # Prepare persistence payload
        backtest_run = {
            "backtest_id": self.backtest_id,
            "name": self.config.get('name', 'Unnamed Backtest'),
            "config": self.config,
            "start_date": candles[0].ts if candles else None,
            "end_date": candles[-1].ts if candles else None,
            "initial_capital": self.engine.initial_capital,
            "final_equity": summary['final_equity'],
            "total_trades": summary['total_trades'],
            "sharpe_ratio": summary['sharpe_ratio'],
            "max_drawdown": summary['max_drawdown']
        }
        
        # Store in DB
        BacktestRepository.save_backtest_run(backtest_run)
        
        # Attribution analysis (Regime/Strategy)
        attribution = self._calculate_attribution(trades)
        
        system_logger.info(f"Backtest {self.backtest_id} completed. Sharpe: {summary['sharpe_ratio']:.2f}")
        
        return {
            "backtest_id": self.backtest_id,
            "summary": summary,
            "attribution": attribution,
            "trades": trades
        }

    def _calculate_attribution(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates PnL contribution by regime and strategy."""
        if not trades: return {}
        
        import pandas as pd
        df = pd.DataFrame(trades)
        
        regime_attr = df.groupby('regime')['pnl'].sum().to_dict()
        strategy_attr = df.groupby('strategy')['pnl'].sum().to_dict()
        
        return {
            "by_regime": regime_attr,
            "by_strategy": strategy_attr
        }
