import asyncio
from typing import List, Dict
from src.data.adapters.mt5_adapter import MT5Adapter
from src.data.ingestion.tick_cleaner import TickCleaner
from src.data.news.collector import AsyncNewsSidecar
from src.regime.mtf_engine import MTFRegimeEngine
from src.strategies.registry import StrategyRouter
from src.risk.asset_aware_risk import MultiAssetRiskEngine
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.execution.engine.base import ExecutionEngine
from src.core.utils.logger import system_logger

class DualChannelTradingNode:
    """
    PHASE 13: Dual-Channel Trading Architecture.
    Separates the real-time MT5 Execution Channel from the Async Information Path.
    """
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        
        # 1. FAST TRADING PATH (Execution Channel)
        self.mt5 = MT5Adapter()
        self.cleaners = {s: TickCleaner(s) for s in symbols}
        self.regime_engine = MTFRegimeEngine()
        self.strategy_router = StrategyRouter()
        # Risk engine now carries the EventRiskOverlay internally
        self.risk_engine = MultiAssetRiskEngine(specs={}) 
        self.exec_engine = ExecutionEngine()
        self.candle_history: Dict[str, List[Candle]] = {s: [] for s in symbols}
        
        # 2. ASYNC INFORMATION PATH (Sidecar)
        self.news_sidecar = AsyncNewsSidecar(symbols)
        
    async def run(self):
        """Starts both channels."""
        # Start the Async Sidecar in the background
        news_task = asyncio.create_task(self.news_sidecar.start())
        
        # MT5 Connect
        if not self.mt5.connect():
            return
            
        system_logger.log_event("TRADING_NODE_LIVE", {"mode": "DUAL_CHANNEL"})
        
        # MAIN EXECUTION LOOP (High Priority)
        try:
            while True:
                for symbol in self.symbols:
                    # A. TICKET INGESTION (Low Latency)
                    tick = self.mt5.get_latest_tick(symbol)
                    if not tick: continue
                    
                    # B. FAST PROCESSING
                    new_candle, closed_candle = self.cleaners[symbol].process_tick(tick)
                    
                    if new_candle and closed_candle:
                        self.candle_history[symbol].append(closed_candle)
                        if len(self.candle_history[symbol]) > 500:
                            self.candle_history[symbol].pop(0)

                        if len(self.candle_history[symbol]) < 50:
                            continue

                        # 1. TECHNICAL REGIME DETECTION (Independent of News)
                        regime_state = self.regime_engine.classify(self.candle_history[symbol], symbol) # Full history
                        
                        # Phase 13: Monitoring Drift
                        from src.monitoring.drift_engine import GlobalMonitoringEngine
                        from src.instruments.behavior_engine import BehaviorEngine
                        monitor = GlobalMonitoringEngine.get_monitor(symbol)
                        
                        # Calculate and record behavior scores
                        b_scores = BehaviorEngine.get_behavior_profile(self.candle_history[symbol], symbol)
                        monitor.record_behavior_scores(b_scores)
                        
                        # 2. STRATEGY SIGNALS (Technical Only)
                        ideas = self.strategy_router.get_trade_ideas(symbol, self.candle_history[symbol], regime_state)
                        
                        # 3. RISK GATING (Optionally applies News Overlay if available)
                        for idea in ideas:
                            # internally checks GlobalEventCache and BehavioralValidator
                            valid, reason = self.risk_engine.validate_trade(
                                idea, size=1.0, equity=100000.0, regime_state=regime_state, candles=self.candle_history[symbol]
                            )
                            
                            if valid:
                                # Calculate Size
                                size = self.risk_engine.get_position_sizing(
                                    symbol, vol=0.01, equity=100000.0, stop_dist=abs(idea.entry_price - idea.stop_loss),
                                    regime_state=regime_state, idea=idea, candles=self.candle_history[symbol]
                                )
                                # 4. EXECUTION
                                from src.core.types.trading import ExecutionOrder
                                from src.core.contracts.instrument_registry import InstrumentRegistry
                                session = InstrumentRegistry.get_session(tick.ts, symbol)
                                
                                order = ExecutionOrder(
                                    id=f"live_{symbol}_{tick.ts.timestamp()}",
                                    symbol=symbol,
                                    side="buy" if idea.direction == "long" else "sell",
                                    type="market",
                                    price=tick.last,
                                    size=size,
                                    timestamp=tick.ts
                                )
                                self.exec_engine.execute_at_tick(
                                    order, tick.last, session, 
                                    vol=0.0001, regime=RegimeType(regime_state.regime_type),
                                    b_scores=b_scores
                                )
                                
                await asyncio.sleep(0.1) # 100ms Loop
        except Exception as e:
            system_logger.log_event("CRITICAL_NODE_FAILURE", {"error": str(e)})
        finally:
            self.news_sidecar.stop()
            await news_task
            self.mt5.disconnect()
