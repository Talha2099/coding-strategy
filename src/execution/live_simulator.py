import time
from typing import List, Dict, Any, Optional
from src.core.types.trading import Candle, StrategySignal
from src.data.ingestion.mt5_ingestor import MT5Ingestor
from src.features.pipeline import FeaturePipeline
from src.backtest.engine import BacktestEngine
from src.infra.database.repositories.trade_repo import TradeRepository
from src.infra.database.repositories.decision_repo import DecisionRepository
from src.core.utils.logger import system_logger

class LiveSimulator:
    """
    STAGE L: Live-testing / Shadow Bot mode.
    Consumes live quotes and executes simulated paper trades.
    """
    def __init__(self, symbol: str, timeframe: str, strategy: Any):
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = strategy
        self.mt5 = MT5Ingestor()
        self.pipeline = FeaturePipeline()
        self.engine = BacktestEngine(initial_capital=100000.0) # Paper capital
        self.is_running = False

    def start(self, interval_seconds: int = 60):
        """Main loop for live simulation."""
        self.is_running = True
        system_logger.info(f"Live Simulation started for {self.symbol} ({self.timeframe})")
        
        while self.is_running:
            try:
                # 1. Fetch live data
                candles_raw = self.mt5.fetch_candles(self.symbol, self.timeframe, count=200)
                if not candles_raw: 
                    time.sleep(5)
                    continue
                
                # Convert to Candle objects
                candles = [Candle(**c) for c in candles_raw]
                
                # 2. Extract Features (Scalar state for latest bar)
                market_state = self.pipeline.get_latest_state(candles, symbol=self.symbol, store=True)
                
                # 3. Strategy Evaluation
                signal: Optional[StrategySignal] = self.strategy.evaluate(candles)
                
                if signal:
                    system_logger.info(f"LIVE SIGNAL: {signal.strategy_name} {signal.direction} at {signal.entry_price}")
                    
                    # Log Decision (Phase 6)
                    DecisionRepository.log_event(
                        event_type="SETUP",
                        ref_id=str(signal.id) if hasattr(signal, 'id') else "N/A",
                        market_snapshot=market_state,
                        decision={"signal": str(signal)}
                    )
                    
                    # 4. Simulated Execution
                    self.engine._handle_signal(signal, timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'), metadata=market_state)
                
                # 5. Monitor existing positions
                self.engine._update_stops(candles[-1].close, timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'))
                
            except Exception as e:
                system_logger.error(f"Live Simulation Loop Error: {e}")
                
            time.sleep(interval_seconds)

    def stop(self):
        self.is_running = False
        system_logger.info("Live Simulation stopped.")
