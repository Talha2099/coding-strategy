from typing import Dict, Any, Optional
from src.core.types.trading import TradeIdea, MicrostructureFeatures
import numpy as np

class MicrostructureValidator:
    """
    Experimental layer for validating trade ideas using L2/Tick data context.
    Provides secondary confirmation before execution.
    """
    def __init__(self, ofi_threshold: float = 0.5):
        self.ofi_threshold = ofi_threshold

    def validate_idea(self, 
                      idea: TradeIdea, 
                      micro: Optional[MicrostructureFeatures] = None) -> Dict[str, Any]:
        """
        Re-validates entry timing using microstructure intel.
        """
        if not micro:
            return {"valid": True, "confidence": 1.0, "reason": "NO_MICRO_DATA"}

        # 1. OFI Alignment Check
        # Example: we want OFI to be positive for long, negative for short
        ofi = micro.order_flow_imbalance
        if idea.direction == "long" and ofi < -self.ofi_threshold:
            return {"valid": False, "confidence": 0.4, "reason": "OFI_OPPOSING_TREND"}
        if idea.direction == "short" and ofi > self.ofi_threshold:
            return {"valid": False, "confidence": 0.4, "reason": "OFI_OPPOSING_TREND"}

        # 2. Liquidity / Imbalance Check
        # High imbalance at the bid/ask might suggest immediate pressure
        imbalance = micro.imbalance
        if idea.direction == "long" and imbalance < -0.3: # Sell pressure
            return {"valid": True, "confidence": 0.8, "reason": "LIQUIDITY_PRESSURE_SELL_SIDE"}

        # 3. Spread Stress Check
        if micro.spread > 0.0005: # High spread for current asset
             return {"valid": True, "confidence": 0.7, "reason": "WIDENING_SPREAD"}

        return {"valid": True, "confidence": 1.0, "reason": "MICRO_CONFIRMED"}
