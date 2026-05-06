import uuid
from datetime import datetime
from typing import Literal
from src.core.types.trading import ScoredTrade, ExecutionOrder, FillResult

class ExecutionEngine:
    def __init__(self, commission_per_lot: float = 5.0):
        self.commission_per_lot = commission_per_lot

    def decide_order_type(self, trade: ScoredTrade) -> Literal["market", "limit"]:
        """
        Microstructure-aware decision: use limit if spread/ofi is favorable, else market.
        """
        ofi = trade.features.get("ofi", 0.0)
        spread = trade.features.get("spread", 0.0)
        
        # If order flow is trending strongly in our direction, we might use a market order 
        # to ensure we don't miss the move (price is 'running away').
        if abs(ofi) > 0.7:
            return "market"
            
        # If spread is wide, try to capturing spread via limit order.
        if spread > 0.0002: # Example threshold for FX
            return "limit"
            
        return "market"

    def estimate_slippage(self, order: ExecutionOrder) -> float:
        """
        Heuristic slippage model based on trade intensity and volatility.
        """
        # In a real system, this would use a Square Root impact model.
        return 0.00005 # 0.5 pip base

    def execute(self, order: ExecutionOrder) -> FillResult:
        """
        Simulates execution. In live, this would route to a broker (OANDA/MT5/IB).
        """
        # Heuristic fill price
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
