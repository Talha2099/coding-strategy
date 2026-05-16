import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.core.types.trading import Candle, Position, FillResult, ExecutionOrder, StrategySignal, TradeCandidate
from src.infra.database.repositories.market_data_repo import MarketDataRepository
from src.infra.database.repositories.trade_repo import TradeRepository
from src.infra.database.repositories.decision_repo import DecisionRepository
from src.backtest.metrics import BacktestMetrics

class BacktestEngine:
    """
    Event-driven backtest engine simulating full trade lifecycle.
    """
    def __init__(self, initial_capital: float = 100000.0, commission: float = 0.0001, slippage: float = 0.0001):
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.positions: Dict[str, Position] = {}
        self.trades_history: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

    def run(self, symbol: str, timeframe: str, candles: List[Candle], strategy_logic: Any):
        """
        Main loop through candles.
        """
        for i in range(50, len(candles)): # Start with some buffer for indicators
            current_time = candles[i].ts
            current_price = candles[i].close
            lookback = candles[:i+1]
            
            # 1. Update existing positions (Check TP/SL)
            self._update_stops(current_price, current_time)
            
            # 2. Strategy Evaluation
            signal: Optional[StrategySignal] = strategy_logic.evaluate(lookback)
            
            if signal:
                self._handle_signal(signal, current_time)
                
        # Close remaining positions at last price
        last_price = candles[-1].close
        last_time = candles[-1].ts
        for pos_id in list(self.positions.keys()):
            self._close_position(pos_id, last_price, last_time, "BACKTEST_END")

        return self.trades_history

    def _get_execution_costs(self, direction: str, current_price: float, metadata: Dict[str, Any]) -> float:
        """
        Calculates dynamic slippage and spread based on session/volatility.
        """
        # Base slippage
        base_slip = self.slippage
        
        # Volatility multiplier (if available in metadata)
        vol_factor = metadata.get("volatility_intensity", 1.0)
        dynamic_slip = base_slip * vol_factor
        
        # Session multiplier (Spread is usually wider in ASIA/NY_CLOSE)
        session = metadata.get("session_label", 2) # Default LONDON
        session_multiplier = 1.0
        if session in [1, 4]: # ASIA or NY_CLOSE
            session_multiplier = 1.5
            
        total_slippage_price = current_price * dynamic_slip * session_multiplier
        
        return total_slippage_price

    def _handle_signal(self, signal: StrategySignal, timestamp: datetime, metadata: Dict[str, Any] = {}):
        """Gating and Execution Simulation."""
        if signal.symbol in [p.symbol for p in self.positions.values()]:
            return
            
        # Realistic Fill
        slip_cost = self._get_execution_costs(signal.direction, signal.entry_price, metadata)
        fill_price = signal.entry_price + (slip_cost if signal.direction == "long" else -slip_cost)
        
        # Size calculation based on signal or default
        size = 100 # Placeholder
        
        pos_id = str(uuid.uuid4())
        pos = Position(
            id=pos_id,
            symbol=signal.symbol,
            asset_class=signal.asset_class,
            size=size if signal.direction == "long" else -size,
            entry_price=fill_price,
            avg_price=fill_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_ts=timestamp,
            strategy_name=signal.strategy_name,
            regime_at_entry=signal.regime_type,
            lifecycle_phase_at_entry=signal.lifecycle_phase,
            metadata=metadata
        )
        
        self.positions[pos_id] = pos
        
        # Log Decision (Phase 6)
        DecisionRepository.log_event(
            event_type="EXECUTION",
            ref_id=pos_id,
            market_snapshot=metadata,
            decision={
                "order_type": "MARKET_SIM",
                "intended_entry": signal.entry_price,
                "filled_price": fill_price,
                "slippage": slip_cost,
                "quantity": size
            }
        )

        self.events.append({
            "type": "ENTRY",
            "pos_id": pos_id,
            "ts": timestamp,
            "price": fill_price,
            "strategy": signal.strategy_name
        })

    def _update_stops(self, price: float, timestamp: datetime):
        for pos_id, pos in list(self.positions.items()):
            # Long position
            if pos.size > 0:
                if price <= pos.stop_loss:
                    self._close_position(pos_id, pos.stop_loss, timestamp, "STOP_LOSS")
                elif price >= pos.take_profit:
                    self._close_position(pos_id, pos.take_profit, timestamp, "TAKE_PROFIT")
            # Short position
            else:
                if price >= pos.stop_loss:
                    self._close_position(pos_id, pos.stop_loss, timestamp, "STOP_LOSS")
                elif price <= pos.take_profit:
                    self._close_position(pos_id, pos.take_profit, timestamp, "TAKE_PROFIT")

    def _close_position(self, pos_id: str, price: float, timestamp: datetime, reason: str):
        pos = self.positions.pop(pos_id)
        
        # PnL Calculation
        pnl = (price - pos.entry_price) * pos.size
        # Apply costs
        costs = (abs(pos.size) * price * self.commission)
        net_pnl = pnl - (costs * 2) # Entry and Exit
        
        self.equity += net_pnl
        
        trade_record = {
            "pos_id": pos_id,
            "symbol": pos.symbol,
            "entry_ts": pos.entry_ts,
            "exit_ts": timestamp,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "pnl": net_pnl,
            "reason": reason,
            "regime": pos.regime_at_entry,
            "strategy": pos.strategy_name
        }
        
        self.trades_history.append(trade_record)
        
        # Log Decision (Phase 6)
        DecisionRepository.log_event(
            event_type="EXIT",
            ref_id=pos_id,
            market_snapshot={}, # Exit snapshot could be added here
            decision={"reason": reason, "exit_price": price},
            outcome={"pnl": net_pnl}
        )

        self.events.append({
            "type": "EXIT",
            "pos_id": pos_id,
            "ts": timestamp,
            "price": price,
            "pnl": net_pnl,
            "reason": reason
        })
