import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.core.contracts.instrument_spec import AssetClass, InstrumentSpec
from src.core.contracts.instrument_registry import InstrumentRegistry
from src.core.types.strategy import TradeIdea, StrategyFamily, RegimeType, StrategyPhase
from src.core.types.trading import RegimeState
from src.risk.event_overlay import EventRiskOverlay

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
        self.event_overlay = EventRiskOverlay()
        self.exposure: Dict[str, float] = {} # Symbol -> Notional
        self.class_exposure: Dict[AssetClass, float] = {ac: 0.0 for ac in AssetClass}
        self.strategy_exposure: Dict[StrategyFamily, float] = {sf: 0.0 for sf in StrategyFamily}
        self.daily_pnl: Dict[str, float] = {} 
        self.total_daily_pnl = 0.0
        self.max_drawdown_limit = 0.12 # 12% Max DD limit (Tightened)
        self.high_water_mark = 0.0
        self.current_equity = 0.0
        
        # Cooldowns and Success tracking
        self.strategy_performance: Dict[str, List[bool]] = {} # strategy_name -> list of recent wins/losses
        self.consecutive_losses: Dict[str, int] = {} # counter for losses
        self.cooldowns: Dict[str, datetime] = {} # symbol or strategy -> expiry
        
        # Risk Limits
        self.limit_per_class = {
            AssetClass.COMMODITY: 0.2, # Reduced commodity cap
            AssetClass.INDEX: 0.4,
            AssetClass.FOREX: 1.0,
            AssetClass.EQUITY: 0.3,
            AssetClass.CRYPTO: 0.1
        }
        self.limit_per_strategy = {
            StrategyFamily.TREND: 0.4,
            StrategyFamily.BREAKOUT: 0.25,
            StrategyFamily.PULLBACK: 0.3,
            StrategyFamily.MEAN_REVERSION: 0.15,
            StrategyFamily.RANGE: 0.15,
            StrategyFamily.GAP: 0.05
        }
        self.max_daily_loss_pct = 0.025 # 2.5% Max Daily Loss
        self.max_risk_per_trade = 0.02 # Hard cap at 2%
        self.correlation_matrix: Optional[np.ndarray] = None
        self.symbols_in_corr: List[str] = []

    def set_equity(self, equity: float):
        self.current_equity = equity
        if equity > self.high_water_mark:
            self.high_water_mark = equity

    def update_performance(self, strategy_name: str, symbol: str, is_win: bool, now: datetime):
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = []
            self.consecutive_losses[strategy_name] = 0
            
        self.strategy_performance[strategy_name].append(is_win)
        if not is_win:
            self.consecutive_losses[strategy_name] += 1
        else:
            self.consecutive_losses[strategy_name] = 0
            
        if len(self.strategy_performance[strategy_name]) > 20:
            self.strategy_performance[strategy_name].pop(0)
            
        # Cooldown logic: if last 3 trades were losses or 3 consecutive losses, 4-hour cooldown
        if self.consecutive_losses[strategy_name] >= 3:
            self.cooldowns[strategy_name] = now + timedelta(hours=4)
            from src.core.utils.logger import system_logger
            system_logger.log_event("STRATEGY_COOLDOWN_TRIGGERED", {
                "strategy": strategy_name,
                "losses": self.consecutive_losses[strategy_name],
                "expiry": (now + timedelta(hours=4)).isoformat()
            })

    def validate_trade(self, 
                       idea: TradeIdea,
                       size: float, 
                       equity: float,
                       regime_state: Optional[RegimeState] = None,
                       current_spread: float = 0.0,
                       now: Optional[datetime] = None,
                       candles: Optional[List[Candle]] = None) -> Tuple[bool, str]:
        symbol = idea.symbol
        spec = self.specs.get(symbol) or InstrumentRegistry.get_spec(symbol)
        if not spec: return False, "INSTRUMENT_NOT_FOUND"
        
        # 0. Cooldown Checks
        if now:
            if symbol in self.cooldowns and now < self.cooldowns[symbol]:
                return False, f"SYMBOL_COOLDOWN_{symbol}"
            if idea.strategy_family.value in self.cooldowns and now < self.cooldowns[idea.strategy_family.value]:
                return False, f"STRATEGY_COOLDOWN_{idea.strategy_family.value}"

        # 0.5 Event Risk Overlay (PHASE 13)
        event_multiplier, event_reason = self.event_overlay.get_event_adjustment(symbol)
        if event_multiplier == 0.0:
            return False, event_reason or "EVENT_RISK_BLOCK"

        # 0.6 Behavioral & Quant Alignment Check (PHASE 13)
        if candles and regime_state:
            from src.scoring.behavioral_validation import BehavioralValidator
            is_aligned, b_score, b_reason = BehavioralValidator.validate_behavioral_alignment(
                idea, candles, regime_state
            )
            if not is_aligned:
                return False, f"BEHAVIORAL_MISALIGNMENT_{b_reason}"
        
        # 0.7 Strategy Alignment Check
        if not InstrumentRegistry.is_strategy_allowed(symbol, idea.strategy_name):
            return False, f"STRATEGY_RESTRICTED_FOR_ASSET_{symbol}"

        # 1. Spread Check
        # Use dynamic spread limit from spec if available
        spread_limit = spec.cost_model.spread_fixed * 3
        if current_spread > spread_limit: 
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
            
        # 4. Max Exposure & Margin
        notional_value = abs(size) * spec.contract_size * spec.point_value
        margin_needed = notional_value * spec.margin_requirement
        if margin_needed > equity * 0.5:
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
        if idea.direction == "short":
            if not spec.allow_short:
                 return False, "SHORTING_FORBIDDEN"
            # Asset behavior check for shorting (e.g. some stocks are dangerous to short)
            if spec.behavior.short_penalty_multiplier > 1.5:
                 return False, "SHORTING_RISK_TOO_HIGH"
            
        # 8. Event and Gap Risk
        if regime_state:
            news_sens = spec.behavior.news_sensitivity
            if hasattr(regime_state, "event_proximity") and regime_state.event_proximity < 30: # 30 mins
                 if news_sens > 0.7:
                      return False, "NEWS_EVENT_PROXIMITY_RISK"
            
            if hasattr(regime_state, "gap_risk"):
                 if spec.behavior.gap_frequency > 0.5 and regime_state.gap_risk > 0.6:
                      return False, "HIGH_GAP_RISK_REJECTION"

        # 9. Regime-based De-risking
        if regime_state:
            from src.core.types.strategy import RegimeType
            if regime_state.regime_type in [RegimeType.VOLATILE_UNSTABLE.value, RegimeType.REVERSAL_RISK.value]:
                return False, "UNSTABLE_REGIME_KILL_SWITCH"
            
            # Late trend protection embedded in validation
            if regime_state.exhaustion_risk > 0.9:
                return False, "EXHAUSTION_RISK_TOO_HIGH"

            # Range Integrity Protection
            if idea.strategy_family == StrategyFamily.RANGE and regime_state.regime_type in [
                RegimeType.RANGE_EXHAUSTION.value, 
                RegimeType.RANGE_BROKEN_UPSIDE.value, 
                RegimeType.RANGE_BROKEN_DOWNSIDE.value,
                RegimeType.RANGE_TO_TREND.value
            ]:
                return False, f"RANGE_INTEGRITY_COMPROMISED_{regime_state.regime_type}"
            
        return True, "SUCCESS"

    def get_position_sizing(self, 
                           symbol: str, 
                           volatility: float, 
                           equity: float, 
                           stop_dist: float,
                           regime_state: RegimeState,
                           idea: Optional[TradeIdea] = None,
                           confidence_score: float = 0.5,
                           rr: float = 2.0,
                           candles: Optional[List[Candle]] = None) -> float:
        """
        Volatility-scaled sizing, regime-aware, health-aware.
        Implements late-entry penalty and overextension de-risking.
        Enhanced with Strategic Interaction scaling (Trap/Sweep).
        """
        from src.core.math_engine.finance_models import KellyCriterion
        from src.core.types.strategy import RegimeType, StrategyPhase
        
        spec = self.specs[symbol]
        
        # 1. Base Risk
        base_risk_pct = min(self.risk_per_trade, self.max_risk_per_trade)
        
        # 2. Kelly Guidance 
        kelly_fraction = KellyCriterion.calculate_fraction(confidence_score, rr, fraction_cap=0.1)
        guided_risk_pct = 0.6 * base_risk_pct + 0.4 * kelly_fraction
        
        # 3. Regime and Health Scaling
        multiplier = 1.0
        
        # 3.0 Event Risk Scaling (Phase 13)
        event_multiplier, _ = self.event_overlay.get_event_adjustment(symbol)
        multiplier *= event_multiplier
        
        # 3.1 Behavior-Aware Sizing (PHASE 13)
        from src.instruments.behavior_engine import BehaviorEngine
        b_scores = BehaviorEngine.get_behavior_profile(candles, symbol) if candles else {}
        
        if b_scores:
            # 3.1.1 Volatility Intensity Scaling
            vol_int = b_scores.get("volatility_intensity", 0.5)
            if vol_int > 0.8: # High volatility regime
                multiplier *= 0.6
                
            # 3.1.2 Fake Breakout Risk Scaling
            if idea and idea.strategy_family == StrategyFamily.BREAKOUT:
                f_prob = b_scores.get("fake_breakout_prob", 0.5)
                if f_prob > 0.6:
                    multiplier *= (1.0 - (f_prob - 0.6) * 2) # Steep decay
            
            # 3.1.3 Trend Quality Confidence
            if idea and idea.strategy_family == StrategyFamily.TREND:
                t_quality = b_scores.get("trend_quality", 0.5)
                if t_quality > 0.8:
                    multiplier *= 1.3 # Allow pyramiding or larger size on high quality trends
        
        # 3.2 Instrument Specific Scaling
        # Boost size for instruments with high trend persistence if in a trend regime
        is_trending = regime_state.regime_type in [RegimeType.CONFIRMED_TREND.value, RegimeType.MID_TREND.value]
        if is_trending and spec.behavior.trend_persistence > 0.7:
            multiplier *= 1.2
            
        # Short-side penalty for equities (Phase 7)
        if idea and idea.direction == "short" and spec.asset_class == AssetClass.EQUITY:
            multiplier *= (1.0 / spec.behavior.short_penalty_multiplier)
        
        regime = RegimeType(regime_state.regime_type)
        
        # Strategic Interaction Modeling (Game Theory Scaling)
        if idea and idea.metadata:
            # Boost for strategic traps (reclaim after sweep)
            if idea.metadata.get("is_sweep"):
                multiplier *= 1.3
            elif idea.metadata.get("trap_detected"):
                multiplier *= 1.2
            
            # De-risk if it's a 'crowded' or 'standard' fade without trap confirmation
            if idea.metadata.get("entry_style") == "fade_edge" and not idea.metadata.get("trap_detected"):
                multiplier *= 0.7
            
            # De-risk on acceptance (breakout risk)
            if idea.metadata.get("breakout_risk", 0) > 0.5:
                multiplier *= 0.6

        # Trend Lifecycle Awareness
        if regime in [RegimeType.EARLY_TREND, RegimeType.TREND_IGNITION, RegimeType.BREAKOUT_ACTIVE]:
             multiplier *= 1.2
        elif regime in [RegimeType.CONFIRMED_TREND, RegimeType.MID_TREND]:
            multiplier *= 1.0 # Standard size
        elif regime in [RegimeType.LATE_TREND, RegimeType.TREND_EXHAUSTION, RegimeType.EXHAUSTION_RISK]:
            multiplier *= 0.5 # Scale down at the end
        elif regime in [RegimeType.REVERSAL_RISK, RegimeType.TREND_FAILED, RegimeType.VOLATILE_UNSTABLE]:
            multiplier *= 0.2 # Extreme caution
        elif regime == RegimeType.PRE_TREND_COMPRESSION:
            multiplier *= 0.8 # Anticipatory entry de-risking
            
        # Range Lifecycle Awareness
        elif regime in [RegimeType.RANGE_ESTABLISHED, RegimeType.RANGE_HIGH_TOUCH, RegimeType.RANGE_LOW_TOUCH]:
            multiplier *= 1.1 # High confidence in range
        elif regime in [RegimeType.RANGE_FORMING, RegimeType.MEAN_REVERSION_SETUP]:
            multiplier *= 0.8 # Scaling in/Early confidence
        elif regime in [RegimeType.RANGE_EXHAUSTION, RegimeType.RANGE_EXPANSION_ATTEMPT]:
            multiplier *= 0.5 # De-risk at potential end of range
        elif regime in [RegimeType.RANGE_BROKEN_UPSIDE, RegimeType.RANGE_BROKEN_DOWNSIDE, RegimeType.RANGE_TO_TREND]:
            multiplier *= 0.1 # Should be blocked but just in case
            
        # 4. Health and Persistence Scaling
        health_mult = getattr(regime_state, "health_score", 0.5) 
        persistence = getattr(regime_state, "persistence", 0.5)
        
        # Composite multiplier: (0.3 floor + up to 0.7 from health/persistence)
        quality_mult = (0.3 + 0.35 * health_mult + 0.35 * persistence)
        multiplier *= quality_mult
        
        # 5. Overextension Penalty
        overextension = getattr(regime_state, "overextension", 0.0)
        if overextension > 2.5:
            multiplier *= 0.5 # Severe overextension
        elif overextension > 1.5:
            multiplier *= 0.8 # Mild overextension
            
        exhaustion = getattr(regime_state, "exhaustion_risk", 0.0)
        if exhaustion > 0.8:
            multiplier *= 0.3
        elif exhaustion > 0.6:
            multiplier *= 0.6
            
        # 6. Lifecycle Phase Penalty (Legacy compatibility + refinement)
        if hasattr(regime_state, "lifecycle_stage"):
            stage = regime_state.lifecycle_stage
            if stage >= 5: # Late stages
                multiplier *= 0.6
            elif stage == 0: # Compression/Ignition
                multiplier *= 1.1

        final_risk_pct = guided_risk_pct * multiplier
        risk_amount = equity * final_risk_pct
        
        # 7. Size Calculation
        adjusted_stop_dist = stop_dist * spec.stop_widening_factor
        raw_size = risk_amount / (adjusted_stop_dist * spec.point_value + 1e-9)
        
        # 8. Correlation Scaling
        if self.correlation_matrix is not None and symbol in self.symbols_in_corr:
            idx = self.symbols_in_corr.index(symbol)
            avg_corr = np.mean(self.correlation_matrix[idx])
            if avg_corr > 0.6:
                raw_size *= (1.0 - (avg_corr - 0.6) * 2) # Steep decay for correlation
        
        final_size = max(spec.min_lot, round(raw_size / spec.lot_step) * spec.lot_step)
        
        from src.core.utils.logger import system_logger
        system_logger.log_event("RISK_SIZING_CALCULATION", {
            "symbol": symbol,
            "multiplier": multiplier,
            "base_risk": base_risk_pct,
            "final_size": final_size,
            "regime": regime.name
        })
        
        return final_size
