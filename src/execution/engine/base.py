import uuid
import numpy as np
from datetime import datetime
from typing import Literal, Dict
from src.core.types.trading import ScoredTrade, ExecutionOrder, FillResult
from src.core.math_engine.finance_models import ExpectancyCalculator
from src.core.math_engine.stochastic_calculus import MicrostructureSDE
from src.core.contracts.spec import InstrumentSpec, SessionType, AssetClass

class ExecutionEngine:
    def __init__(self, specs: Dict[str, InstrumentSpec], commission_per_lot: float = 5.0):
        self.specs = specs
        self.commission_per_lot = commission_per_lot
        self.sde_model = MicrostructureSDE(theta=0.5, mu=0.0001, sigma=0.0001)

    def get_realtime_spread(self, symbol: str, session: SessionType) -> float:
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
        return base * multipliers.get(session, 1.0)

    def decide_order_type(self, trade: ScoredTrade, session: SessionType) -> Literal["market", "limit"]:
        """
        Microstructure-aware decision: use limit if spread/ofi is favorable, else market.
        Uses Expectancy criteria and Session awareness.
        """
        spec = self.specs.get(trade.symbol)
        ofi = trade.features.get("ofi", 0.0)
        spread = self.get_realtime_spread(trade.symbol, session)
        
        # Calculate expectancy of current trade
        edge = ExpectancyCalculator.calculate(trade.probability, 2.0)
        
        # Avoid market orders in illiquid sessions
        if session == SessionType.CLOSE or (spec and spread > spec.spread_base * 3):
            return "limit"

        if edge < 0.05:
            return "market" if ofi > 0.8 else "limit"

        if abs(ofi) > 0.7:
            return "market"
            
        if spread > 0.0002:
            return "limit"
            
        return "market"

    def estimate_slippage(self, order: ExecutionOrder, current_vol: float = 0.0001) -> float:
        """
        Volatility-scaled slippage model using SDE simulation logic.
        """
        spec = self.specs.get(order.symbol)
        base_spread = spec.spread_base if spec else 0.0001
        
        # Model spread mean-reversion
        simulated_spreads = self.sde_model.simulate_path(base_spread, dt=1/60, steps=10)
        expected_spread = float(np.mean(simulated_spreads))
        
        # Scale by volatility (Fast markets increase slippage)
        vol_scaler = 1.0 + (current_vol * 1000)
        
        return expected_spread * 0.5 * vol_scaler

    def execute(self, order: ExecutionOrder, session: SessionType, vol: float = 0.0001) -> FillResult:
        """
        Simulates execution with session and volatility context.
        """
        slippage = self.estimate_slippage(order, vol)
        fill_price = order.price + slippage if order.side == "buy" else order.price - slippage
        
        return FillResult(
            order_id=order.id,
            fill_price=fill_price,
            fill_size=order.size,
            slippage=slippage,
            commission=self.commission_per_lot * order.size,
            timestamp=datetime.now()
        )
