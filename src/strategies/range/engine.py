from typing import List, Optional, Dict, Any
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily, StrategyPhase
from src.core.contracts.spec import InstrumentSpec
from src.strategies.base import BaseStrategy

from src.strategies.range.analysis import RangeAnalysisEngine
from src.strategies.range.planning import RangePlanningEngine
from src.strategies.range.execution import RangeExecutionEngine
from src.strategies.range.management import RangeManagementEngine

class RangeTradingLifecycleEngine(BaseStrategy):
    """
    Implements a complete range-trading lifecycle.
    Uses dedicated engines for Analysis, Planning, Execution, and Management.
    """
    def __init__(self, name: str, spec: InstrumentSpec, subtype: str = "lifecycle"):
        super().__init__(name, StrategyFamily.RANGE, spec)
        self.subtype = subtype
        self.current_phase = StrategyPhase.ANALYSIS
        
        # Internal Engines
        self.analyzer = RangeAnalysisEngine()
        self.planner = RangePlanningEngine()
        self.executor = RangeExecutionEngine()
        self.manager = RangeManagementEngine()

    def is_valid_regime(self, regime: RegimeType) -> bool:
        return regime in [
            RegimeType.RANGE, RegimeType.RANGE_FORMING, RegimeType.RANGE_ESTABLISHED,
            RegimeType.MEAN_REVERTING, RegimeType.MID_RANGE, RegimeType.VOLATILE_UNSTABLE
        ]

    def analyze_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState]) -> Dict[str, Any]:
        if not mtf_state:
            # Fallback for STF
            mtf_state = MTFRegimeState(regime_state.symbol, regime_state, regime_state, regime_state, "neutral", 0.0, regime_state.timestamp)
        return self.analyzer.analyze(candles, mtf_state)

    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        self.current_phase = StrategyPhase.ANALYSIS
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        
        # Log Analysis
        from src.core.utils.logger import system_logger
        system_logger.log_event("RANGE_ANALYSIS", {
            "symbol": regime_state.symbol,
            "regime": regime_state.regime_type,
            "health": analysis["health"],
            "hurst": analysis["hurst"],
            "quality": analysis["quality_score"],
            "is_rangy": analysis["is_rangy"]
        })

        self.current_phase = StrategyPhase.PLANNING
        plan = self.planner.plan(candles, analysis)
        
        if plan:
            system_logger.log_event("RANGE_PLAN_CREATED", {
                "symbol": regime_state.symbol,
                "entry_style": plan["entry_style"],
                "direction": "long" if plan["direction"] == 1 else "short",
                "risk_pct": plan["risk_pct"]
            })
            self.current_phase = StrategyPhase.SETUP_DETECTED
            return True
        return False

    def confirm_entry(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        analysis = self.analyze_setup(candles, regime_state, mtf_state)
        plan = self.planner.plan(candles, analysis)
        if not plan: return False
        
        self.current_phase = StrategyPhase.EXECUTION
        if self.executor.check_trigger(candles, plan, analysis):
            from src.core.utils.logger import system_logger
            system_logger.log_event("RANGE_ENTRY_TRIGGERED", {
                "symbol": regime_state.symbol,
                "entry_style": plan["entry_style"],
                "direction": "long" if plan["direction"] == 1 else "short"
            })
            self.current_phase = StrategyPhase.ENTRY_TRIGGERED
            return True
        return False

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict[str, Any]]:
        self.current_phase = StrategyPhase.MANAGEMENT
        updates = self.manager.evaluate(candles, idea, regime_state)
        
        if updates:
            from src.core.utils.logger import system_logger
            if updates.get("exit"):
                system_logger.log_event("RANGE_EXIT_DECISION", {
                    "symbol": idea.symbol,
                    "reason": updates.get("exit_reason"),
                    "pnl": (candles[-1].close - idea.entry_price) * (1 if idea.direction == "long" else -1)
                })
            elif "partial_exit" in updates:
                 system_logger.log_event("RANGE_PARTIAL_EXIT", {
                    "symbol": idea.symbol,
                    "size": updates["partial_exit"]
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
        direction = "long" if plan["direction"] == 1 else "short"
        
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
            take_profit=plan["targets"][-1],
            risk_reward_ratio=abs(plan["targets"][-1] - entry) / (abs(entry - plan["stop_loss"]) + 1e-9),
            confidence_score=analysis["quality_score"],
            regime_tag=RegimeType(regime_state.regime_type),
            lifecycle_phase=self.current_phase,
            invalidation_price=plan["invalidation"],
            timestamp=candles[-1].ts,
            metadata={
                **plan["metadata"],
                "targets": plan["targets"],
                "range_health": analysis["health"]
            }
        )

    def define_stop(self, candles: List[Candle]) -> float:
        # Fallback for contract
        return candles[-1].close * 0.99

    def define_target(self, candles: List[Candle]) -> float:
        # Fallback for contract
        return candles[-1].close * 1.01
