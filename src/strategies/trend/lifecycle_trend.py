from typing import List, Optional, Dict, Any
from datetime import datetime
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.contracts.spec import InstrumentSpec
from src.strategies.base import BaseStrategy
from src.features.technical_engine import TechnicalFeatureEngine

from src.strategies.trend.analysis import TrendAnalysisEngine
from src.strategies.trend.planning import TrendPlanningEngine
from src.strategies.trend.execution import TrendExecutionEngine
from src.strategies.trend.management import TrendManagementEngine

class LifecycleTrendStrategy(BaseStrategy):
    """
    Institutional-grade Trend Following Lifecycle Engine.
    Uses dedicated engines for Analysis, Planning, Execution, and Management.
    """
    def __init__(self, spec: InstrumentSpec):
        super().__init__("LifecycleTrend", StrategyFamily.TREND, spec)
        self.lookback = 200
        self.current_phase = StrategyPhase.ANALYSIS
        
        # Internal Engines
        self.analyzer = TrendAnalysisEngine()
        self.planner = TrendPlanningEngine()
        self.executor = TrendExecutionEngine()
        self.manager = TrendManagementEngine()

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [
            RegimeType.EARLY_TREND, RegimeType.CONFIRMED_TREND,
            RegimeType.MID_TREND, RegimeType.PULLBACK_IN_TREND,
            RegimeType.CONTINUATION_READY, RegimeType.PRE_TREND_COMPRESSION,
            RegimeType.LATE_TREND # Valid for management or opportunistic pullback
        ]

    def analyze_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState]) -> Dict[str, Any]:
        """Phase 1: ANALYSIS"""
        # If no MTF state provided (e.g. single timeframe test), we wrap the LTF state
        if not mtf_state:
            mtf_state = MTFRegimeState(regime_state.symbol, regime_state, regime_state, regime_state, "neutral", 0.0, regime_state.timestamp)
        
        return self.analyzer.analyze(candles, mtf_state)

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        self.current_phase = StrategyPhase.ANALYSIS
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        
        # Log Analysis
        from src.core.utils.logger import system_logger
        system_logger.log_event("TREND_ANALYSIS", {
            "symbol": regime_state.symbol,
            "regime": regime_state.regime_type,
            "health": analysis["health"],
            "persistence": analysis["persistence"],
            "quality": analysis["quality_score"],
            "is_trending": analysis["is_trending"]
        })

        # Phase 2: PLANNING
        self.current_phase = StrategyPhase.PLANNING
        plan = self.planner.plan(candles, analysis)
        
        if plan:
            system_logger.log_event("TREND_PLAN_CREATED", {
                "symbol": regime_state.symbol,
                "entry_style": plan["entry_style"],
                "risk_pct": plan["risk_pct"],
                "invalidation": plan["invalidation"]
            })
            self.current_phase = StrategyPhase.SETUP_DETECTED
            return True
        else:
             system_logger.log_event("TREND_PLAN_REJECTED", {
                "symbol": regime_state.symbol,
                "reason": "exhausted_or_low_quality" if analysis["is_trending"] else "no_trend"
            })
            
        return False

    def confirm_entry(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """Phase 3: EXECUTION"""
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        plan = self.planner.plan(candles, analysis)
        if not plan: return False
        
        self.current_phase = StrategyPhase.EXECUTION
        if self.executor.check_trigger(candles, plan, analysis):
            from src.core.utils.logger import system_logger
            system_logger.log_event("TREND_ENTRY_TRIGGERED", {
                "symbol": regime_state.symbol,
                "entry_style": plan["entry_style"],
                "direction": analysis["direction"]
            })
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            return True
            
        return False

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict[str, Any]]:
        """Phase 4: MANAGEMENT & Phase 5: EXIT"""
        self.current_phase = StrategyPhase.MANAGEMENT
        updates = self.manager.evaluate(candles, idea, regime_state)
        
        if updates:
            from src.core.utils.logger import system_logger
            if updates.get("exit"):
                system_logger.log_event("TREND_EXIT_DECISION", {
                    "symbol": idea.symbol,
                    "reason": updates.get("exit_reason"),
                    "pnl_estimate": (candles[-1].close - idea.entry_price) * (1 if idea.direction == "long" else -1)
                })
            elif "stop_loss" in updates:
                 system_logger.log_event("TREND_STOP_TRAILED", {
                    "symbol": idea.symbol,
                    "new_sl": updates["stop_loss"]
                })
        
        return updates

    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        return float(analysis["quality_score"])

    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        plan = self.planner.plan(candles, analysis)
        if not plan: return None
        
        entry = candles[-1].close
        direction = "long" if analysis["direction"] == 1 else "short"
        
        return TradeIdea(
            symbol=symbol,
            asset_class=self.spec.asset_class,
            timeframe="M5",
            strategy_name=self.name,
            strategy_family=self.family,
            strategy_subtype=plan["entry_style"],
            direction=direction,
            entry_price=entry,
            stop_loss=plan["stop_loss"],
            take_profit=plan["targets"][1],
            risk_reward_ratio=abs(plan["targets"][1] - entry) / abs(entry - plan["stop_loss"] + 1e-9),
            confidence_score=analysis["quality_score"],
            regime_tag=RegimeType(regime_state.regime_type),
            lifecycle_phase=StrategyPhase.POSITION_OPEN,
            invalidation_price=plan["invalidation"],
            holding_period_hint="swing",
            timestamp=candles[-1].ts,
            metadata={
                **plan["metadata"],
                "targets": plan["targets"],
                "health": analysis["health"],
                "hurst": analysis["hurst"],
                "persistence": analysis["persistence"],
                "htf_alignment": analysis["htf_alignment"]
            }
        )

    def define_stop(self, candles: List[Candle]) -> float:
        # Not used individually as planning handles it, but implemented for contract
        features = TechnicalFeatureEngine.get_candle_features(candles)
        return candles[-1].close - (features["atr"][-1] * 2.0)

    def define_target(self, candles: List[Candle]) -> float:
        features = TechnicalFeatureEngine.get_candle_features(candles)
        return candles[-1].close + (features["atr"][-1] * 4.0)
