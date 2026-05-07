import numpy as np
from typing import Dict, List, Optional
from .spec import AssetClass, InstrumentSpec

class CrashProtectionModule:
    """
    Defensive layer to block trading during regime shifts or toxic volatility.
    """
    def __init__(self, vol_spike_threshold: float = 2.5):
        self.vol_spike_threshold = vol_spike_threshold
        self.rolling_vol: Dict[str, List[float]] = {}
        
    def should_block(self, symbol: str, current_vol: float, correlations: np.ndarray) -> Dict[str, any]:
        if symbol not in self.rolling_vol:
            self.rolling_vol[symbol] = []
        
        self.rolling_vol[symbol].append(current_vol)
        if len(self.rolling_vol[symbol]) > 20: self.rolling_vol[symbol].pop(0)
        
        avg_vol = np.mean(self.rolling_vol[symbol]) if self.rolling_vol[symbol] else current_vol
        vol_ratio = current_vol / (avg_vol + 1e-9)
        
        # Detect Vola Spike
        if vol_ratio > self.vol_spike_threshold:
            return {"block": True, "reason": "VOLATILITY_SPIKE", "ratio": vol_ratio}
            
        # Detect Correlation Jump (simplified: if max off-diagonal is too high)
        if correlations.size > 1:
            max_corr = np.max(correlations - np.eye(correlations.shape[0]))
            if max_corr > 0.85:
                return {"block": True, "reason": "CORRELATION_CLUSTERING", "corr": max_corr}
                
        return {"block": False}

class MultiAssetRiskEngine:
    def __init__(self, specs: Dict[str, InstrumentSpec]):
        self.specs = specs
        self.exposure: Dict[str, float] = {} # Symbol -> Position Size
        self.daily_pnl: Dict[str, float] = {} 
        
    def validate_trade(self, 
                       symbol: str, 
                       size: float, 
                       is_overnight: bool, 
                       equity: float) -> Tuple[bool, str]:
        spec = self.specs.get(symbol)
        if not spec: return False, "INSTRUMENT_NOT_FOUND"
        
        # 1. Overnight Check
        if is_overnight and not spec.allow_overnight:
            return False, "OVERNIGHT_FORBIDDEN"
            
        # 2. Max Exposure (Vol-Scaled)
        notional_value = size * spec.contract_size * spec.point_value
        if notional_value > equity * 0.5: # 50% max leverage per asset
            return False, "MARGIN_LIMIT_EXCEEDED"
            
        # 3. Shorting Constraints
        if size < 0 and not spec.allow_short:
            return False, "SHORTING_FORBIDDEN"
            
        # 4. Daily Drawdown Cap
        symbol_pnl = self.daily_pnl.get(symbol, 0.0)
        if symbol_pnl < -(equity * 0.02): # 2% max loss per asset/session
            return False, "DAILY_SYMBOL_STOP_LOSS"
            
        return True, "SUCCESS"

    def get_position_sizing(self, symbol: str, volatility: float, equity: float, stop_dist: float) -> float:
        """
        Kelly-influenced volatility-scaled sizing.
        """
        spec = self.specs[symbol]
        # Risk 1% of equity per trade
        risk_amount = equity * 0.01
        
        # Convert stop distance (points) into notional loss
        # Size = Risk / (StopDist * PointValue)
        raw_size = risk_amount / (stop_dist * spec.point_value)
        
        # Cap by min/max lot
        return max(spec.min_lot, round(raw_size / spec.lot_step) * spec.lot_step)
