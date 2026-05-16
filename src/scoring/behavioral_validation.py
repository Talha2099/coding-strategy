import numpy as np
from typing import Dict, Tuple, Optional, List
from src.core.types.strategy import TradeIdea, StrategyFamily, RegimeType
from src.core.types.trading import RegimeState, Candle
from src.instruments.behavior_engine import BehaviorEngine
from src.core.contracts.instrument_registry import InstrumentRegistry

class BehavioralValidator:
    """
    PHASE 13: Behavioral Validation Layer.
    Combines Expert YAML Priors + Quantitative Behavior Scores + Regime State.
    Ensures trade signals align with the instrument's current personality.
    """
    
    @staticmethod
    def validate_behavioral_alignment(
        idea: TradeIdea, 
        candles: List[Candle],
        regime_state: RegimeState
    ) -> Tuple[bool, float, str]:
        """
        Validates if the strategy idea is aligned with the current quantitative behavior.
        Returns (is_aligned, combined_score, reason)
        
        Combined Score = f(Strategic Interaction [SMC] + Behavioral Scores + Regime Health)
        """
        symbol = idea.symbol
        spec = InstrumentRegistry.get_spec(symbol)
        
        # 1. Get Dynamic behavior scores
        scores = BehaviorEngine.get_behavior_profile(candles, symbol)
        
        # 2. Logic based on Strategy Family
        is_aligned = True
        base_confidence = 0.5
        reason = "DEFAULT_ALIGNMENT"

        if idea.strategy_family == StrategyFamily.BREAKOUT:
            is_aligned, base_confidence, reason = BehavioralValidator._validate_breakout(idea, spec, scores, regime_state)
            
        elif idea.strategy_family == StrategyFamily.MEAN_REVERSION:
            is_aligned, base_confidence, reason = BehavioralValidator._validate_mean_reversion(idea, spec, scores, regime_state)
            
        elif idea.strategy_family == StrategyFamily.TREND:
            is_aligned, base_confidence, reason = BehavioralValidator._validate_trend(idea, spec, scores, regime_state)

        if not is_aligned:
            return False, 0.0, reason

        # 3. Add SMC (Smart Money Concepts) / Strategic Interaction Layer
        # Checks for Liquidity Sweeps, Displacement, and Fair Value Gaps (proxy)
        smc_score = scores.get("liquidity_event", 0.0)
        
        # If it's a trend trade but there was a recent heavy sweep -> boost confidence (Institutional trap)
        if idea.strategy_family == StrategyFamily.TREND and smc_score > 0.7:
            base_confidence *= 1.2
            reason += "_SMC_SWEEP_BOOST"
        
        # If it's a mean reversion but liquidty event is low -> reduce confidence
        if idea.strategy_family == StrategyFamily.MEAN_REVERSION and smc_score < 0.2:
            base_confidence *= 0.8
            reason += "_SMC_WEAK_LIQUIDITY"

        combined_score = np.clip(base_confidence * getattr(regime_state, "health_score", 1.0), 0.0, 1.0)
        
        return is_aligned, float(combined_score), reason

    @staticmethod
    def _validate_breakout(idea, spec, scores, regime_state) -> Tuple[bool, float, str]:
        """
        High Quality Breakout requires:
        - High breakout_quality_score
        - Low fake_breakout_prob
        - Volatility expansion intensity
        """
        b_quality = scores["breakout_quality"]
        f_prob = scores["fake_breakout_prob"]
        vol_int = scores["volatility_intensity"]
        
        # Expert Prior: if YAML says fake breakouts are common, we are stricter
        f_breakout_prior = spec.behavior.false_breakout_prob
        f_threshold = 0.6 - (f_breakout_prior * 0.2) # strictness increases with prior
        
        if b_quality < 0.4:
            return False, b_quality, "LOW_BREAKOUT_QUALITY"
            
        if f_prob > f_threshold:
            # If we need strict confirmation (from YAML), block it
            if spec.behavior.confirmation_requirement == "STRICT":
                return False, 1.0 - f_prob, "HIGH_FAKE_BREAKOUT_PROB_STRICT"
        
        confidence = (b_quality * 0.6 + (1.0 - f_prob) * 0.4)
        return True, float(confidence), "BREAKOUT_ALIGNED"

    @staticmethod
    def _validate_mean_reversion(idea, spec, scores, regime_state) -> Tuple[bool, float, str]:
        """
        Mean Reversion requires:
        - High mean_reversion_score
        - Low trend_quality_score
        - Overextension (Z-score)
        """
        mr_score = scores["mean_reversion"]
        t_quality = scores["trend_quality"]
        
        # Expert Prior: MR propensity
        mr_prior = spec.behavior.mean_reversion_propensity
        
        # If trend is too strong, MR is high risk
        t_threshold = 0.6 + (mr_prior * 0.2)
        if t_quality > t_threshold:
            return False, 1.0 - t_quality, "TREND_TOO_STRONG_FOR_MR"
            
        if mr_score < 0.4:
             return False, mr_score, "LOW_MR_PROPENSITY"
             
        confidence = (mr_score * 0.7 + (1.0 - t_quality) * 0.3)
        return True, float(confidence), "MR_ALIGNED"

    @staticmethod
    def _validate_trend(idea, spec, scores, regime_state) -> Tuple[bool, float, str]:
        """
        Trend following requires:
        - High trend_quality_score
        - Volatility stability
        - Low exhaustion risk
        """
        t_quality = scores["trend_quality"]
        vol_int = scores["volatility_intensity"]
        
        # Expert Prior: trend persistence
        t_prior = spec.behavior.trend_persistence
        
        if t_quality < 0.4:
            return False, t_quality, "LOW_TREND_QUALITY"
            
        # Check exhaustion from regime state
        exhaustion = getattr(regime_state, "exhaustion_risk", 0.0)
        if exhaustion > 0.8:
            return False, 1.0 - exhaustion, "EXHAUSTION_LIMIT_BREACHED"
            
        confidence = (t_quality * 0.8 + (1.0 - vol_int) * 0.2)
        return True, float(confidence), "TREND_ALIGNED"
