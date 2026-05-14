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
        self.exposure: Dict[str, float] = {} # Symbol -> Notional
        self.class_exposure: Dict[AssetClass, float] = {ac: 0.0 for ac in AssetClass}
        self.strategy_exposure: Dict[StrategyFamily, float] = {sf: 0.0 for sf in StrategyFamily}
        self.daily_pnl: Dict[str, float] = {} 
        self.total_daily_pnl = 0.0
        self.max_drawdown_limit = 0.15 # 15% Max DD limit
        self.high_water_mark = 0.0
        self.current_equity = 0.0
        
        # Cooldowns and Success tracking
        self.strategy_performance: Dict[str, List[bool]] = {} # strategy_name -> list of recent wins/losses
        self.cooldowns: Dict[str, datetime] = {} # symbol or strategy -> expiry
        
        # Risk Limits
        self.limit_per_class = {
            AssetClass.CFD: 1.0, 
            AssetClass.STOCK: 0.5,
            AssetClass.FOREX: 1.2,
            AssetClass.CRYPTO: 0.2
        }
        self.limit_per_strategy = {
            StrategyFamily.TREND: 0.5,
            StrategyFamily.BREAKOUT: 0.3,
            StrategyFamily.PULLBACK: 0.4,
            StrategyFamily.MEAN_REVERSION: 0.2,
            StrategyFamily.RANGE: 0.2,
            StrategyFamily.GAP: 0.1
        }
        self.max_daily_loss_pct = 0.03 # 3% Max Daily Loss
        self.correlation_matrix: Optional[np.ndarray] = None
        self.symbols_in_corr: List[str] = []

    def set_equity(self, equity: float):
        self.current_equity = equity
        if equity > self.high_water_mark:
            self.high_water_mark = equity

    def update_performance(self, strategy_name: str, symbol: str, is_win: bool, now: datetime):
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = []
        self.strategy_performance[strategy_name].append(is_win)
        if len(self.strategy_performance[strategy_name]) > 10:
            self.strategy_performance[strategy_name].pop(0)
            
        # Cooldown logic: if last 3 trades were losses, 4-hour cooldown
        recent = self.strategy_performance[strategy_name][-3:]
        if len(recent) == 3 and not any(recent):
            self.cooldowns[strategy_name] = now + timedelta(hours=4)

    def validate_trade(self, 
                       idea: TradeIdea,
                       size: float, 
                       equity: float,
                       regime_state: Optional[RegimeState] = None,
                       current_spread: float = 0.0,
                       now: Optional[datetime] = None) -> Tuple[bool, str]:
        symbol = idea.symbol
        spec = self.specs.get(symbol)
        if not spec: return False, "INSTRUMENT_NOT_FOUND"
        
        # 0. Cooldown Checks
        if now:
            if symbol in self.cooldowns and now < self.cooldowns[symbol]:
                return False, f"SYMBOL_COOLDOWN_{symbol}"
            if idea.strategy_family.value in self.cooldowns and now < self.cooldowns[idea.strategy_family.value]:
                return False, f"STRATEGY_COOLDOWN_{idea.strategy_family.value}"

        # 1. Spread Check
        if current_spread > spec.spread_base * 3: 
            return False, "SPREAD_TOO_WIDE"

        # 2. Daily/Drawdown Limits
        if self.total_daily_pnl < -(equity * self.max_daily_loss_pct):
            return False, "TOTAL_DAILY_LOSS_LIMIT_REACHED"
            
        current_dd = (self.high_water_mark - equity) / (self.high_water_mark + 1e-9)
        if current_dd > self.max_drawdown_limit:
            return False, "MAX_DRAWDOWN_BREACHED_KILL_SWITCH"

        # 3. Overnight Check
        is_overnight = idea.holding_period_hint != "intraday"
        if is_overnight and not spec.allow_overnight:
            return False, "OVERNIGHT_FORBIDDEN"
            
        # 4. Max Exposure
        notional_value = abs(size) * spec.contract_size * spec.point_value
        if notional_value > equity * 0.5:
            return False, "MARGIN_LIMIT_EXCEEDED"
            
        # 5. Strategy Family Limits
        curr_strat_exp = self.strategy_exposure.get(idea.strategy_family, 0.0)
        strat_limit = self.limit_per_strategy.get(idea.strategy_family, 0.5) * equity
        if curr_strat_exp + notional_value > strat_limit:
            return False, f"STRATEGY_LIMIT_REACHED_{idea.strategy_family.value}"

        # 6. Asset Class Limits
        current_class_exp = self.class_exposure.get(spec.asset_class, 0.0)
        class_limit = self.limit_per_class.get(spec.asset_class, 1.0) * equity
        if current_class_exp + notional_value > class_limit:
            return False, f"ASSET_CLASS_LIMIT_REACHED_{spec.asset_class.value}"
            
        # 7. Shorting Constraints
        if idea.direction == "short" and not spec.allow_short:
            return False, "SHORTING_FORBIDDEN"
            
        # 8. Regime-based De-risking
        if regime_state:
            from src.core.types.strategy import RegimeType
            if regime_state.regime_type in [RegimeType.VOLATILE_UNSTABLE.value, RegimeType.REVERSAL_RISK.value]:
                return False, "UNSTABLE_REGIME_KILL_SWITCH"
            
            # Late trend protection embedded in validation
            if regime_state.exhaustion_risk > 0.9:
                return False, "EXHAUSTION_RISK_TOO_HIGH"
            
        return True, "SUCCESS"

    def get_position_sizing(self, 
                           symbol: str, 
                           volatility: float, 
                           equity: float, 
                           stop_dist: float,
                           regime_state: RegimeState,
                           confidence_score: float = 0.5,
                           rr: float = 2.0) -> float:
        """
        Volatility-scaled sizing, regime-aware, health-aware.
        """
        from src.core.math_engine.finance_models import KellyCriterion
        from src.core.types.strategy import RegimeType
        
        spec = self.specs[symbol]
        
        # 1. Base Risk
        base_risk_pct = self.risk_per_trade
        
        # 2. Kelly Guidance 
        kelly_fraction = KellyCriterion.calculate_fraction(confidence_score, rr, fraction_cap=0.1)
        guided_risk_pct = 0.6 * base_risk_pct + 0.4 * kelly_fraction
        
        # 3. Regime and Health Scaling
        multiplier = 1.0
        regime = RegimeType(regime_state.regime_type)
        
        if regime == RegimeType.VOLATILE_UNSTABLE:
            multiplier = 0.1
        elif regime in [RegimeType.EARLY_TREND, RegimeType.TREND_IGNITION]:
            multiplier = 1.2 # Be aggressive early
        elif regime in [RegimeType.LATE_TREND, RegimeType.TREND_EXHAUSTION]:
            multiplier = 0.5 # Scale down at the end
            
        # 4. Health-based adjustment
        health_mult = regime_state.health_score # 0 to 1
        multiplier *= (0.5 + 0.5 * health_mult) # 0.5x block to 1.0x full
        
        # 5. Overextension / Exhaustion Penalty
        if regime_state.overextension > 2.0:
            multiplier *= 0.7
        if regime_state.exhaustion_risk > 0.7:
            multiplier *= 0.5
            
        final_risk_pct = guided_risk_pct * multiplier
        risk_amount = equity * final_risk_pct
        
        # 6. Size Calculation
        adjusted_stop_dist = stop_dist * spec.stop_widening_factor
        raw_size = risk_amount / (adjusted_stop_dist * spec.point_value + 1e-9)
        
        # 7. Correlation Scaling (Optional adjustment)
        if self.correlation_matrix is not None and symbol in self.symbols_in_corr:
            idx = self.symbols_in_corr.index(symbol)
            avg_corr = np.mean(self.correlation_matrix[idx])
            if avg_corr > 0.7:
                raw_size *= 0.7 # Reduction for highly correlated asset
        
        return max(spec.min_lot, round(raw_size / spec.lot_step) * spec.lot_step)
