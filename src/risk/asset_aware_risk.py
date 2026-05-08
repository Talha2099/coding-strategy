import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .spec import AssetClass, InstrumentSpec
from src.core.types.strategy import TradeIdea, StrategyFamily

class CrashProtectionModule:
    """
    Defensive layer to block trading during regime shifts or toxic volatility.
    Supports dynamic scaling and cooldown periods.
    """
    def __init__(self, vol_spike_threshold: float = 2.5, cooldown_minutes: int = 60):
        self.vol_spike_threshold = vol_spike_threshold
        self.cooldown_minutes = cooldown_minutes
        self.rolling_vol: Dict[str, List[float]] = {}
        self.cooldowns: Dict[str, datetime] = {}
        
    def get_scaling_factor(self, symbol: str, current_vol: float) -> float:
        """Returns a size multiplier between 0.0 and 1.0 based on volatility regime."""
        if symbol not in self.rolling_vol or not self.rolling_vol[symbol]:
            return 1.0
        
        avg_vol = np.mean(self.rolling_vol[symbol])
        vol_ratio = current_vol / (avg_vol + 1e-9)
        
        if vol_ratio > self.vol_spike_threshold: return 0.0 # Hard block
        if vol_ratio > 1.5: return 0.5 # De-risk
        return 1.0

    def should_block(self, symbol: str, current_vol: float, correlations: np.ndarray, now: datetime = None) -> Dict[str, any]:
        # Check active cooldowns
        if now and symbol in self.cooldowns:
            if now < self.cooldowns[symbol]:
                return {"block": True, "reason": "COOLDOWN_ACTIVE"}
        
        if symbol not in self.rolling_vol:
            self.rolling_vol[symbol] = []
        
        self.rolling_vol[symbol].append(current_vol)
        if len(self.rolling_vol[symbol]) > 20: self.rolling_vol[symbol].pop(0)
        
        avg_vol = np.mean(self.rolling_vol[symbol]) if self.rolling_vol[symbol] else current_vol
        vol_ratio = current_vol / (avg_vol + 1e-9)
        
        # Detect Vola Spike
        if vol_ratio > self.vol_spike_threshold:
            if now: self.cooldowns[symbol] = now + timedelta(minutes=self.cooldown_minutes)
            return {"block": True, "reason": "VOLATILITY_SPIKE", "ratio": vol_ratio}
            
        # Detect Correlation Jump
        if correlations.size > 1:
            max_corr = np.max(correlations - np.eye(correlations.shape[0]))
            if max_corr > 0.85:
                return {"block": True, "reason": "CORRELATION_CLUSTERING", "corr": max_corr}
                
        return {"block": False}

class MultiAssetRiskEngine:
    def __init__(self, specs: Dict[str, InstrumentSpec], risk_per_trade: float = 0.01):
        self.specs = specs
        self.risk_per_trade = risk_per_trade
        self.exposure: Dict[str, float] = {} # Symbol -> Position Size
        self.class_exposure: Dict[AssetClass, float] = {ac: 0.0 for ac in AssetClass}
        self.strategy_exposure: Dict[StrategyFamily, float] = {sf: 0.0 for sf in StrategyFamily}
        self.daily_pnl: Dict[str, float] = {} 
        
        # Risk Limits
        self.limit_per_class = {
            AssetClass.CFD: 1.0, # 100% of equity
            AssetClass.STOCK: 0.5, # 50% of equity
        }
        self.limit_per_strategy = {
            StrategyFamily.BREAKOUT: 0.3,
            StrategyFamily.PULLBACK: 0.4,
            StrategyFamily.MEAN_REVERSION: 0.2,
            StrategyFamily.RANGE: 0.2,
            StrategyFamily.GAP: 0.1
        }
        
    def validate_trade(self, 
                       idea: TradeIdea,
                       size: float, 
                       equity: float) -> Tuple[bool, str]:
        symbol = idea.symbol
        spec = self.specs.get(symbol)
        if not spec: return False, "INSTRUMENT_NOT_FOUND"
        
        # 1. Overnight Check
        is_overnight = idea.holding_period_hint != "intraday"
        if is_overnight and not spec.allow_overnight:
            return False, "OVERNIGHT_FORBIDDEN"
            
        # 2. Max Exposure (Vol-Scaled)
        notional_value = abs(size) * spec.contract_size * spec.point_value
        if notional_value > equity * 0.5:
            return False, "MARGIN_LIMIT_EXCEEDED"
            
        # 3. Strategy Family Limits
        curr_strat_exp = self.strategy_exposure.get(idea.strategy_family, 0.0)
        strat_limit = self.limit_per_strategy.get(idea.strategy_family, 0.5) * equity
        if curr_strat_exp + notional_value > strat_limit:
            return False, f"STRATEGY_LIMIT_REACHED_{idea.strategy_family.value}"

        # 4. Asset Class Limits
        current_class_exp = self.class_exposure.get(spec.asset_class, 0.0)
        class_limit = self.limit_per_class.get(spec.asset_class, 1.0) * equity
        if current_class_exp + notional_value > class_limit:
            return False, f"ASSET_CLASS_LIMIT_REACHED_{spec.asset_class.value}"
            
        # 5. Shorting Constraints
        if idea.direction == "short" and not spec.allow_short:
            return False, "SHORTING_FORBIDDEN"
            
        # 6. Daily Drawdown Cap
        symbol_pnl = self.daily_pnl.get(symbol, 0.0)
        if symbol_pnl < -(equity * 0.02):
            return False, "DAILY_SYMBOL_STOP_LOSS"
            
        return True, "SUCCESS"

    def get_position_sizing(self, symbol: str, volatility: float, equity: float, stop_dist: float) -> float:
        """
        Kelly-influenced volatility-scaled sizing.
        """
        spec = self.specs[symbol]
        # Risk X% of equity per trade
        risk_amount = equity * self.risk_per_trade
        
        # Convert stop distance (points) into notional loss
        # Size = Risk / (StopDist * PointValue)
        raw_size = risk_amount / (stop_dist * spec.point_value)
        
        # Cap by min/max lot
        return max(spec.min_lot, round(raw_size / spec.lot_step) * spec.lot_step)
