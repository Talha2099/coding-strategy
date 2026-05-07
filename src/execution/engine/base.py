import uuid
from datetime import datetime
from typing import Literal
from src.core.types.trading import ScoredTrade, ExecutionOrder, FillResult
from src.core.math_engine.finance_models import ExpectancyCalculator
from src.core.math_engine.stochastic_calculus import MicrostructureSDE

class ExecutionEngine:
    def __init__(self, commission_per_lot: float = 5.0):
        self.commission_per_lot = commission_per_lot
        self.sde_model = MicrostructureSDE(theta=0.5, mu=0.0001, sigma=0.0001)

    def decide_order_type(self, trade: ScoredTrade) -> Literal["market", "limit"]:
        """
        Microstructure-aware decision: use limit if spread/ofi is favorable, else market.
        Uses Expectancy criteria.
        """
        ofi = trade.features.get("ofi", 0.0)
        spread = trade.features.get("spread", 0.0)
        
        # Calculate expectancy of current trade
        edge = ExpectancyCalculator.calculate(trade.probability, 2.0) # Assume 2.0 RR for simplicity
        
        if edge < 0.05:
            # Low edge, need to be very aggressive on execution or skip
            return "market" if ofi > 0.8 else "limit"

        # If order flow is trending strongly in our direction, we might use a market order 
        if abs(ofi) > 0.7:
            return "market"
            
        # If spread is wide, try to capturing spread via limit order.
        if spread > 0.0002:
            return "limit"
            
        return "market"

    def estimate_slippage(self, order: ExecutionOrder) -> float:
        """
        Heuristic slippage model using SDE simulation logic.
        """
        # Model spread mean-reversion
        simulated_spreads = self.sde_model.simulate_path(0.0001, dt=1/60, steps=10)
        expected_spread = float(np.mean(simulated_spreads))
        
        return expected_spread * 0.5

    def execute(self, order: ExecutionOrder) -> FillResult:
        """
        Simulates execution. In live, this would route to a broker.
        """
        import numpy as np # Needed for slippage calculation if not imported
        slippage = self.estimate_slippage(order)
        fill_price = order.price + slippage if order.side == "buy" else order.price - slippage
        
        return FillResult(
            order_id=order.id,
            fill_price=fill_price,
            fill_size=order.size,
            slippage=slippage,
            commission=self.commission_per_lot * order.size,
            timestamp=datetime.now()
        )
