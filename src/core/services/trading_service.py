from typing import List, Dict, Any, Optional
from src.data.ingestion.yahoo_finance import YahooFinanceIngestor
from src.backtest.backtest_runner import BacktestRunner
from src.backtest.walk_forward import WalkForwardEngine
from src.execution.live_simulator import LiveSimulator
from src.infra.database.repositories.market_data_repo import MarketDataRepository
from src.core.utils.logger import system_logger

class TradingSystemService:
    """
    STAGE P: Unified Service Interface.
    Orchestrates ingestion, research, and simulation.
    """
    
    @staticmethod
    def ingest_data(symbol: str, timeframe: str, start_date: str):
        """Historical data ingestion entry point."""
        return YahooFinanceIngestor.fetch_historical(symbol, timeframe, start_date)

    @staticmethod
    def run_backtest(config: Dict[str, Any], symbol: str, timeframe: str, strategy: Any):
        """Runs and stores a backtest."""
        # Get data from DB
        candles_raw = MarketDataRepository.get_candles(symbol, timeframe, limit=5000)
        from src.core.types.trading import Candle
        candles = [Candle(**c) for c in candles_raw]
        
        runner = BacktestRunner(config)
        return runner.run(symbol, timeframe, candles, strategy)

    @staticmethod
    def run_walk_forward(config: Dict[str, Any], symbol: str, timeframe: str, strategy: Any):
        """Runs rolling window OOS testing."""
        candles_raw = MarketDataRepository.get_candles(symbol, timeframe, limit=5000)
        from src.core.types.trading import Candle
        candles = [Candle(**c) for c in candles_raw]
        
        wf_engine = WalkForwardEngine(config)
        return wf_engine.run(symbol, timeframe, candles, strategy)

    @staticmethod
    def start_shadow_bot(symbol: str, timeframe: str, strategy: Any):
        """Starts live simulation mode."""
        sim = LiveSimulator(symbol, timeframe, strategy)
        # Running in background/thread recommended for real use
        sim.start()
        return sim

    @staticmethod
    def export_data(table_name: str, format: str = "csv", output_path: str = "exports/"):
        """Exports DB tables to common formats."""
        import os
        from src.infra.database.db_manager import db_manager
        
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
            
        data = db_manager.fetch_all(f"SELECT * FROM {table_name}")
        if not data:
            return None
            
        import pandas as pd
        df = pd.DataFrame(data)
        
        file_path = os.path.join(output_path, f"{table_name}.{format}")
        if format == "csv":
            df.to_csv(file_path, index=False)
        elif format == "json":
            df.to_json(file_path, orient="records")
        elif format == "parquet":
            df.to_parquet(file_path)
            
        return file_path
