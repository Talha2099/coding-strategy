from typing import List, Dict, Optional
from src.core.types.strategy import StrategyFamily, RegimeType
from src.core.contracts.instrument_spec import Archetype, SessionType
from dataclasses import dataclass, field

@dataclass
class CompatibilityRule:
    suitable_archetypes: List[Archetype] = field(default_factory=list)
    unsuitable_archetypes: List[Archetype] = field(default_factory=list)
    preferred_regimes: List[RegimeType] = field(default_factory=list)
    unsuitable_regimes: List[RegimeType] = field(default_factory=list)
    preferred_sessions: List[SessionType] = field(default_factory=list)
    min_volatility: float = 0.0
    max_volatility: float = 1.0
    min_trend_strength: float = 0.0
    max_trend_strength: float = 1.0

class StrategyCompatibilityMatrix:
    """Compatibility matrix between strategies and instrument environments"""
    
    _matrix: Dict[StrategyFamily, CompatibilityRule] = {
        StrategyFamily.TREND: CompatibilityRule(
            suitable_archetypes=[Archetype.TREND_HEAVY, Archetype.INDEX_CFD, Archetype.GOLD_CFD, Archetype.US_LARGE_CAP],
            preferred_regimes=[RegimeType.EARLY_TREND, RegimeType.TREND_IGNITION, RegimeType.CONFIRMED_TREND],
            unsuitable_regimes=[RegimeType.RANGE_EXHAUSTION, RegimeType.VOLATILE_UNSTABLE],
            min_trend_strength=0.15
        ),
        StrategyFamily.BREAKOUT: CompatibilityRule(
            suitable_archetypes=[Archetype.INDEX_CFD, Archetype.GOLD_CFD, Archetype.US_SMALL_CAP, Archetype.HIGH_BETA, Archetype.US_LARGE_CAP],
            preferred_regimes=[RegimeType.BREAKOUT_ACTIVE, RegimeType.PRE_TREND_COMPRESSION],
            preferred_sessions=[SessionType.LONDON, SessionType.NEW_YORK],
            min_volatility=0.1,
            max_volatility=0.6, # Avoid extreme instability
            min_trend_strength=0.1
        ),
        StrategyFamily.RANGE: CompatibilityRule(
            suitable_archetypes=[Archetype.RANGE_HEAVY, Archetype.MEAN_REVERTING, Archetype.LOW_BETA],
            preferred_regimes=[RegimeType.RANGE_ESTABLISHED, RegimeType.RANGE_HIGH_TOUCH, RegimeType.MID_RANGE],
            unsuitable_regimes=[RegimeType.TREND_IGNITION, RegimeType.BREAKOUT_ACTIVE, RegimeType.RANGE_BROKEN_UPSIDE, RegimeType.RANGE_BROKEN_DOWNSIDE],
            max_trend_strength=0.3
        ),
        StrategyFamily.MEAN_REVERSION: CompatibilityRule(
            suitable_archetypes=[Archetype.MEAN_REVERTING, Archetype.RANGE_HEAVY, Archetype.US_LARGE_CAP],
            preferred_regimes=[RegimeType.MEAN_REVERSION_SETUP, RegimeType.TREND_EXHAUSTION, RegimeType.LATE_TREND],
            unsuitable_regimes=[RegimeType.TREND_IGNITION, RegimeType.EARLY_TREND],
            min_volatility=0.15 # Needs some 'heat' to mean revert
        ),
        # Assuming GAP is a family
    }

    @classmethod
    def get_suitability_score(cls, 
                               strategy_family: StrategyFamily, 
                               archetype: Archetype, 
                               regime: RegimeType, 
                               session: SessionType,
                               volatility: float,
                               trend_strength: float) -> float:
        """
        Calculates a compatibility score from 0.0 to 1.0
        """
        rule = cls._matrix.get(strategy_family)
        if not rule:
            return 0.5
            
        score = 1.0
        
        # Archetype Check
        if archetype in rule.unsuitable_archetypes:
            return 0.0
        if rule.suitable_archetypes and archetype not in rule.suitable_archetypes:
            score *= 0.6 # Penalty but not hard rejection
            
        # Regime Check
        if regime in rule.unsuitable_regimes:
            return 0.0
        if rule.preferred_regimes and regime not in rule.preferred_regimes:
            score *= 0.7
            
        # Session Check
        if rule.preferred_sessions and session not in rule.preferred_sessions:
            score *= 0.8
            
        # Volatility & Trend Strength
        if volatility < rule.min_volatility or volatility > rule.max_volatility:
            score *= 0.5
        if trend_strength < rule.min_trend_strength or trend_strength > rule.max_trend_strength:
            score *= 0.5
            
        return max(0.0, score)
