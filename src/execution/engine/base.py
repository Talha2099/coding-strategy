import uuid
import numpy as np
from datetime import datetime
from typing import Literal, Dict
from src.core.types.trading import ScoredTrade, ExecutionOrder, FillResult
from src.core.math_engine.finance_models import ExpectancyCalculator
from src.core.math_engine.stochastic_calculus import MicrostructureSDE
from src.core.contracts.instrument_spec import InstrumentSpec, SessionType, AssetClass

from src.core.types.strategy import RegimeType

class ExecutionEngine:
    def __init__(self, specs: Dict[str, InstrumentSpec], commission_per_lot: float = 5.0):
        self.specs = specs
        self.commission_per_lot = commission_per_lot
        self.sde_model = MicrostructureSDE(theta=0.5, mu=0.0001, sigma=0.0001)

    def get_realtime_spread(self, symbol: str, session: SessionType, regime: Optional[RegimeType] = None) -> float:
        spec = self.specs.get(symbol)
        if not spec: return 0.0001
        
        base = spec.cost_model.spread_fixed
        # Session Multipliers from Spec
        session_mult = spec.cost_model.session_spread_multipliers.get(session, 1.0)
        
        regime_mult = 1.0
        if regime:
            if regime == RegimeType.VOLATILE_UNSTABLE: regime_mult = 3.0
            elif regime == RegimeType.TREND_IGNITION: regime_mult = 1.8
            elif regime == RegimeType.BREAKOUT: regime_mult = 1.5
            
        return base * session_mult * regime_mult

    def estimate_slippage(self, order: ExecutionOrder, current_vol: float = 0.0001, regime: Optional[RegimeType] = None) -> float:
        spec = self.specs.get(order.symbol)
        if not spec: return 0.0001
        
        base_bps = spec.cost_model.slippage_base_bps
        
        vol_scaler = 1.0 + (current_vol * 1000)
        regime_scaler = 1.0
        if regime:
            if regime in [RegimeType.VOLATILE_UNSTABLE, RegimeType.GAP_DRIVEN]:
                regime_scaler = 2.0
            elif regime == RegimeType.TREND_IGNITION:
                regime_scaler = 1.6
        
        # In Phase 8, we consider instrument liquidity tier (simulated here)
        liquidity_mult = 1.0 # Default
        if spec.asset_class == AssetClass.EQUITY:
             liquidity_mult = 1.5 # Stocks often have more slippage
             
        # Market orders and Stops (which become market) have slippage
        if order.type == "limit":
             return -0.00001 # Small improvement simulation
             
        # Calculate slippage as bps of price
        slippage_price = (base_bps / 10000.0) * order.price * vol_scaler * regime_scaler * liquidity_mult
        return slippage_price

    def validate_for_execution(self, order: ExecutionOrder, spread: float, regime: Optional[RegimeType] = None) -> Tuple[bool, str]:
        spec = self.specs.get(order.symbol)
        if not spec: return False, "UNKNOWN_INSTRUMENT"
        
        # 1. Spread Rejection
        max_allowed_spread = spec.cost_model.spread_fixed * 3.0
        if regime == RegimeType.VOLATILE_UNSTABLE:
             max_allowed_spread *= 2.0
             
        if spread > max_allowed_spread:
             return False, f"SPREAD_THRESHOLD_EXCEEDED_{spread:.5f} > {max_allowed_spread:.5f}"
             
        # 2. Execution preference check
        if spec.cost_model.execution_type_preference == "limit" and order.type == "market":
             # Optional: warn or reject if strategy is using market but asset prefers limit
             pass

        return True, "READY"

    def execute_at_tick(self, 
                       order: ExecutionOrder, 
                       tick_price: float, 
                       session: SessionType, 
                       vol: float = 0.0001, 
                       regime: Optional[RegimeType] = None,
                       b_scores: Optional[Dict[str, float]] = None) -> Optional[FillResult]:
        """
        Executes order logic against a specific price tick.
        PHASE 13: Behavior-Aware Execution.
        """
        spec = self.specs.get(order.symbol)
        if not spec: return None

        # 1. Behavior-Aware Order Modification (Pre-Execution)
        if b_scores:
            # A. If fake breakout probability is high, forcing Limit Entries
            if b_scores.get("fake_breakout_prob", 0) > 0.7 and order.type == "market":
                # Downgrade to limit at current price mid-execution or skip
                # Simulation: force a slightly worse fill to simulate limit wait
                pass 
                
            # B. If volatility is extreme, widen execution tolerance
            if b_scores.get("volatility_intensity", 0) > 0.8:
                vol *= 1.5 

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
        
        # Determine fill size based on session liquidity AND instrument behavior
        liquidity_map = {
            SessionType.ASIA: 0.8,
            SessionType.LONDON: 1.0,
            SessionType.NEW_YORK: 1.0,
            SessionType.OVERLAP_LN_NY: 1.1,
            SessionType.CLOSE: 0.1
        }
        session_prob = liquidity_map.get(session, 1.0)
        instrument_prob = spec.cost_model.partial_fill_likelihood
        
        fill_prob = session_prob * instrument_prob
        
        fill_size = order.size
        # Simulate partial fills
        if fill_prob < 1.0:
            actual_ratio = float(np.random.uniform(fill_prob * 0.5, 1.0))
            fill_size = order.size * actual_ratio

        return FillResult(
            order_id=order.id,
            fill_price=fill_price,
            fill_size=fill_size,
            slippage=slippage,
            commission=spec.cost_model.commission_per_lot * fill_size,
            timestamp=datetime.now()
        )
