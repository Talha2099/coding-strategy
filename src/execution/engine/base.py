import uuid
import numpy as np
from datetime import datetime
from typing import Literal, Dict
from src.core.types.trading import ScoredTrade, ExecutionOrder, FillResult
from src.core.math_engine.finance_models import ExpectancyCalculator
from src.core.math_engine.stochastic_calculus import MicrostructureSDE
from src.core.contracts.spec import InstrumentSpec, SessionType, AssetClass

from src.core.types.strategy import RegimeType

class ExecutionEngine:
    def __init__(self, specs: Dict[str, InstrumentSpec], commission_per_lot: float = 5.0):
        self.specs = specs
        self.commission_per_lot = commission_per_lot
        self.sde_model = MicrostructureSDE(theta=0.5, mu=0.0001, sigma=0.0001)

    def get_realtime_spread(self, symbol: str, session: SessionType, regime: Optional[RegimeType] = None) -> float:
        spec = self.specs.get(symbol)
        if not spec: return 0.0001
        
        base = spec.spread_base
        # Session Multipliers
        multipliers = {
            SessionType.ASIA: 1.5,
            SessionType.LONDON: 1.0,
            SessionType.NEW_YORK: 1.0,
            SessionType.OVERLAP_LN_NY: 0.8,
            SessionType.CLOSE: 5.0
        }
        
        regime_mult = 1.0
        if regime:
            from src.core.types.strategy import RegimeType
            if regime == RegimeType.VOLATILE_UNSTABLE: regime_mult = 3.0
            elif regime == RegimeType.TREND_IGNITION: regime_mult = 1.8
            elif regime == RegimeType.BREAKOUT: regime_mult = 1.5
            
        return base * multipliers.get(session, 1.0) * regime_mult

    def estimate_slippage(self, order: ExecutionOrder, current_vol: float = 0.0001, regime: Optional[RegimeType] = None) -> float:
        spec = self.specs.get(order.symbol)
        base_spread = spec.spread_base if spec else 0.0001
        
        simulated_spreads = self.sde_model.simulate_path(base_spread, dt=1/60, steps=10)
        expected_spread = float(np.mean(simulated_spreads))
        
        vol_scaler = 1.0 + (current_vol * 1000)
        regime_scaler = 1.0
        if regime:
            from src.core.types.strategy import RegimeType
            if regime in [RegimeType.VOLATILE_UNSTABLE, RegimeType.GAP_DRIVEN]:
                regime_scaler = 2.0
            elif regime == RegimeType.TREND_IGNITION:
                regime_scaler = 1.6
        
        # Limit orders usually have 0 slippage if executed exactly at price (or better)
        # Market orders and Stops (which become market) have slippage
        if order.type == "limit":
             return 0.0
             
        return expected_spread * 0.5 * vol_scaler * regime_scaler

    def execute_at_tick(self, order: ExecutionOrder, tick_price: float, session: SessionType, vol: float = 0.0001, regime: Optional[RegimeType] = None) -> Optional[FillResult]:
        """
        Executes order logic against a specific price tick.
        """
        # Determine if order triggers or executes
        can_execute = False
        execution_price = tick_price
        
        if order.type == "market":
            can_execute = True
        elif order.type == "limit":
            if order.side == "buy" and tick_price <= order.price:
                can_execute = True
                execution_price = order.price # Fill at limit or better (simulating limit)
            elif order.side == "sell" and tick_price >= order.price:
                can_execute = True
                execution_price = order.price
        elif order.type == "stop":
            if order.side == "buy" and tick_price >= order.price:
                can_execute = True
            elif order.side == "sell" and tick_price <= order.price:
                can_execute = True
                
        if not can_execute:
            return None
            
        slippage = self.estimate_slippage(order, vol, regime)
        fill_price = execution_price + slippage if order.side == "buy" else execution_price - slippage
        
        # Determine fill size based on session liquidity
        liquidity_map = {
            SessionType.ASIA: 0.8,
            SessionType.LONDON: 1.0,
            SessionType.NEW_YORK: 1.0,
            SessionType.OVERLAP_LN_NY: 1.1,
            SessionType.CLOSE: 0.1
        }
        fill_prob = liquidity_map.get(session, 1.0)
        
        fill_size = order.size
        if fill_prob < 1.0:
            actual_ratio = float(np.random.uniform(fill_prob * 0.5, 1.0))
            fill_size = order.size * actual_ratio

        return FillResult(
            order_id=order.id,
            fill_price=fill_price,
            fill_size=fill_size,
            slippage=slippage,
            commission=self.commission_per_lot * fill_size,
            timestamp=datetime.now()
        )
