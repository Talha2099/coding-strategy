from src.core.contracts.instrument_spec import (
    InstrumentSpec, AssetClass, InstrumentType, AssetBehavior, 
    CostModel, SessionType, TradingSession, Archetype
)
from src.core.types.strategy import StrategyFamily
from datetime import time
from typing import List

class AssetProfileFactory:
    """Pre-defined behavioral profiles for major asset classes and types"""
    
    @staticmethod
    def get_index_profile(symbol: str) -> InstrumentSpec:
        """Index CFD: High trend persistence, session-driven volatility"""
        profile = InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.INDEX,
            instrument_type=InstrumentType.CFD,
            tick_size=0.1,
            point_value=1.0,
            contract_size=1.0,
            lot_step=0.1,
            min_lot=0.1,
            max_lot=100.0,
            cost_model=CostModel(
                spread_fixed=1.0, 
                slippage_base_bps=1.0,
                session_spread_multipliers={
                    SessionType.ASIA: 2.0,
                    SessionType.NEW_YORK: 1.0,
                    SessionType.LONDON: 1.0
                }
            ),
            margin_requirement=0.05,
            leverage_limit=20,
            behavior=AssetBehavior(
                archetype=Archetype.INDEX_CFD,
                trend_persistence=0.75,
                mean_reversion_propensity=0.35,
                volatility_regime_avg=0.25,
                breakout_success_rate=0.45,
                session_dependency={
                    SessionType.LONDON: 1.2,
                    SessionType.NEW_YORK: 1.5,
                    SessionType.ASIA: 0.4
                },
                failure_modes=["stop_run", "news_spike"],
                preferred_timeframes=["5m", "15m", "1h"],
                event_risk_sensitivity=0.8
            ),
            stop_widening_factor=1.2, # Indices need room for noise
            preferred_strategies=["trend_following", "breakout_expansion", "session_opening_gap"],
            restricted_strategies=["range_fade_heavy_ny"]
        )

        # Specialized logic for US100 and US30
        if symbol == "US100":
            profile.behavior.archetypes = [
                Archetype.MOMENTUM_INDEX,
                Archetype.GROWTH_SENTIMENT,
                Archetype.VOLATILITY_EXPANSION,
                Archetype.TREND_PERSISTENT
            ]
            profile.behavior.trend_persistence = 0.9 # Very High
            profile.behavior.breakout_quality = 0.9   # Very High
            profile.behavior.mean_reversion_propensity = 0.25
            profile.preferred_strategies += ["momentum_pullback", "orb"]
            profile.restricted_strategies += ["static_range_fade", "slow_mean_reversion"]
            profile.metadata["personality"] = "Momentum-driven, rate-sensitive, tech-heavy impulse."
        
        elif symbol == "US30":
            profile.behavior.archetypes = [
                Archetype.MACRO_SENTIMENT_INDEX,
                Archetype.INSTITUTIONAL_ROTATION,
                Archetype.BALANCED_TREND_MR
            ]
            profile.behavior.trend_persistence = 0.75 # High
            profile.behavior.mean_reversion_propensity = 0.6 # Better than US100
            profile.preferred_strategies += ["range_fade", "controlled_mean_reversion"]
            profile.restricted_strategies += ["hyper_aggressive_breakout_chasing"]
            profile.metadata["personality"] = "Smoother, rotational, macro-economic cycle driven."

        return profile

    @staticmethod
    def get_gbpjpy_profile(symbol: str = "GBPJPY") -> InstrumentSpec:
        """GBPJPY: High volatility, carry trade sensitive, deep pullbacks"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.FOREX,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.001,
            point_value=1.0,
            contract_size=100000.0,
            lot_step=0.01,
            min_lot=0.01,
            max_lot=100.0,
            cost_model=CostModel(
                spread_fixed=0.02, # Approx 2 pips
                slippage_base_bps=1.5,
                session_spread_multipliers={SessionType.ASIA: 2.0, SessionType.LATE_NY: 3.0}
            ),
            margin_requirement=0.033, # 1:30
            leverage_limit=30,
            behavior=AssetBehavior(
                archetype=Archetype.HIGH_VOL_FX,
                archetypes=[
                    Archetype.CARRY_TRADE_SENSITIVE,
                    Archetype.TREND_EXPANSION,
                    Archetype.LIQUIDITY_SWEEP_PRONE
                ],
                trend_persistence=0.85, # Very High
                trend_acceleration=0.8,  # High
                volatility_regime_avg=0.4, # Very High
                breakout_quality=0.75,
                false_breakout_prob=0.7,
                mean_reversion_propensity=0.3,
                stop_hunt_probability=0.8,
                event_risk_sensitivity=0.85,
                failure_modes=["v_reversal", "liquidity_sweep", "intervention_shock"],
                preferred_timeframes=["15m", "1h", "4h"],
                session_dependency={
                    SessionType.LONDON: 1.4,
                    SessionType.ASIA: 1.1, # London-Tokyo overlap
                    SessionType.NEW_YORK: 0.9
                }
            ),
            stop_widening_factor=2.0, # Wide stops for GBPJPY volatility
            preferred_strategies=["trend_following", "momentum_breakout", "liquidity_sweep_fade"],
            restricted_strategies=["tight_stop_scalping", "aggressive_mean_reversion"],
            metadata={
                "personality": "Beast from the East. Carry trade sensitive, Tokyo/London interaction.",
                "execution_notes": "Preferred: Trend pullback, liqudity sweep reversal."
            }
        )

    @staticmethod
    def get_gold_profile(symbol: str = "XAUUSD") -> InstrumentSpec:
        """Gold CFD: Volatile, news sensitive, unique liquidity sweeps"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.COMMODITY,
            instrument_type=InstrumentType.CFD,
            tick_size=0.01,
            point_value=1.0,
            contract_size=100.0,
            lot_step=0.01,
            min_lot=0.01,
            max_lot=50.0,
            cost_model=CostModel(
                spread_fixed=0.3, 
                slippage_base_bps=2.5,
                execution_type_preference="limit", # Limit preferred for gold sweeps
                session_spread_multipliers={SessionType.ASIA: 3.0, SessionType.LONDON: 1.0}
            ),
            margin_requirement=0.05,
            leverage_limit=20,
            behavior=AssetBehavior(
                archetype=Archetype.GOLD_CFD,
                archetypes=[
                    Archetype.MACRO_SENSITIVE, 
                    Archetype.LIQUIDITY_DRIVEN, 
                    Archetype.VOLATILITY_EXPANSION, 
                    Archetype.INSTITUTIONAL_MOMENTUM
                ],
                trend_persistence=0.65, # Medium-high
                trend_acceleration=0.8,   # High
                exhaustion_reversal_prob=0.7, # High
                late_trend_risk=0.9,     # Very high
                mean_reversion_propensity=0.4,
                volatility_regime_avg=0.3,
                volatility_clustering=True,
                news_sensitivity=0.95,
                breakout_success_rate=0.35,
                breakout_quality=0.8,    # High
                false_breakout_prob=0.7, # High
                confirmation_requirement="STRICT",
                stop_hunt_probability=0.9, # Very high
                event_risk_sensitivity=1.0, # Max sensitivity
                failure_modes=["fake_breakout", "liquidity_sweep", "news_spike", "stop_run"],
                preferred_timeframes=["15m", "1h", "4h"],
                session_dependency={
                    SessionType.LONDON: 1.3,
                    SessionType.NEW_YORK: 1.5,
                    SessionType.ASIA: 0.5
                }
            ),
            stop_widening_factor=1.8, # Gold needs deep stops to survive sweeps
            preferred_strategies=["trend_following", "volatility_breakout", "liquidity_sweep_fade", "breakout"],
            restricted_strategies=["simple_rsi_overbought", "static_mean_reversion", "low_vol_scalping"],
            metadata={
                "personality": "Macro/Momentum hybrid. Reactive to USD, yields, geopolitics.",
                "session_notes": {
                    "london_open": "Directional expansion. Preferred: Breakout, Trend Continuation.",
                    "overlap": "Peak liquidity. Preferred: Momentum Breakout, Trend Following.",
                    "asian": "Compression. Preferred: Range, Liquidity Mapping."
                }
            }
        )

    @staticmethod
    def get_us_large_cap_profile(symbol: str) -> InstrumentSpec:
        """US Large Cap: High liquidity, benchmark-correlated, stable trends"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            point_value=1.0,
            contract_size=1.0,
            lot_step=1.0,
            min_lot=1.0,
            max_lot=100000.0,
            cost_model=CostModel(
                spread_fixed=0.01, 
                slippage_base_bps=0.2,
                execution_type_preference="market",
                partial_fill_likelihood=0.9
            ),
            margin_requirement=0.25,
            leverage_limit=4,
            behavior=AssetBehavior(
                archetype=Archetype.US_LARGE_CAP,
                trend_persistence=0.65,
                mean_reversion_propensity=0.5,
                gap_frequency=0.4,
                news_sensitivity=0.6,
                failure_modes=["gap_and_crap", "earnings_volatility"]
            ),
            preferred_strategies=["trend_following", "relative_strength", "gap_momentum"]
        )

    @staticmethod
    def get_us_small_cap_profile(symbol: str) -> InstrumentSpec:
        """US Small Cap: More volatile, prone to momentum spikes, lower liquidity"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            point_value=1.0,
            contract_size=1.0,
            lot_step=1.0,
            min_lot=1.0,
            max_lot=50000.0,
            cost_model=CostModel(
                spread_fixed=0.05, 
                slippage_base_bps=2.0,
                execution_type_preference="market",
                partial_fill_likelihood=0.7 # Lower liquidity for small caps
            ),
            margin_requirement=0.5,
            leverage_limit=2,
            behavior=AssetBehavior(
                archetype=Archetype.US_SMALL_CAP,
                trend_persistence=0.5,
                mean_reversion_propensity=0.2, # Proved to momentum
                volatility_regime_avg=0.6,
                gap_frequency=0.6,
                failure_modes=["pump_and_dump", "liquidity_trap"]
            ),
            preferred_strategies=["breakout_momentum", "volatility_expansion"]
        )

    @staticmethod
    def get_high_beta_profile(symbol: str) -> InstrumentSpec:
        """High Beta: Aggressive price moves, follows index with multiplier"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            point_value=1.0,
            contract_size=1.0,
            lot_step=1.0,
            min_lot=1.0,
            max_lot=50000.0,
            cost_model=CostModel(spread_fixed=0.02, slippage_base_bps=1.0),
            margin_requirement=0.3,
            leverage_limit=3,
            behavior=AssetBehavior(
                archetype=Archetype.HIGH_BETA,
                trend_persistence=0.7,
                volatility_regime_avg=0.5,
                news_sensitivity=0.8,
                failure_modes=["v_reversal", "vertical_exhaustion"]
            ),
            preferred_strategies=["trend_following", "breakout_expansion"]
        )

    @staticmethod
    def get_gap_heavy_profile(symbol: str) -> InstrumentSpec:
        """Gap Heavy: Significant overnight/session gaps (e.g. some commodities or specific stocks)"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            point_value=1.0,
            contract_size=1.0,
            lot_step=1.0,
            min_lot=1.0,
            max_lot=100000.0,
            cost_model=CostModel(spread_fixed=0.01, slippage_base_bps=0.5),
            margin_requirement=0.25,
            behavior=AssetBehavior(
                archetype=Archetype.GAP_HEAVY,
                gap_frequency=0.8,
                volatility_regime_avg=0.3,
                failure_modes=["gap_fill_trap", "runaway_gap"]
            ),
            preferred_strategies=["gap_fade", "gap_momentum", "session_opening_range"]
        )

    @staticmethod
    def get_trend_heavy_profile(symbol: str) -> InstrumentSpec:
        """Trend Heavy: Clean directional moves with shallow pullbacks"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.INDEX,
            instrument_type=InstrumentType.CFD,
            tick_size=0.1,
            point_value=1.0,
            contract_size=1.0,
            lot_step=0.1,
            min_lot=0.1,
            max_lot=100.0,
            cost_model=CostModel(),
            margin_requirement=0.05,
            behavior=AssetBehavior(
                archetype=Archetype.TREND_HEAVY,
                trend_persistence=0.85,
                mean_reversion_propensity=0.2,
                failure_modes=["trend_bend", "parabolic_blowoff"]
            ),
            preferred_strategies=["trend_following", "moving_average_cross", "pullback_entry"]
        )

    @staticmethod
    def get_range_heavy_profile(symbol: str) -> InstrumentSpec:
        """Range Heavy: Stays in equilibrium for long periods"""
        return InstrumentSpec(
            symbol=symbol,
            asset_class=AssetClass.FOREX,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.00001,
            point_value=1.0,
            contract_size=100000.0,
            lot_step=0.01,
            min_lot=0.01,
            max_lot=100.0,
            cost_model=CostModel(
                spread_fixed=0.00015,
                session_spread_multipliers={
                    SessionType.ASIA: 2.5,
                    SessionType.LATE_NY: 4.0,
                    SessionType.LONDON: 1.0
                }
            ),
            margin_requirement=0.033,
            behavior=AssetBehavior(
                archetype=Archetype.RANGE_HEAVY,
                mean_reversion_propensity=0.85,
                trend_persistence=0.25,
                failure_modes=["breakout_failure", "churn"]
            ),
            preferred_strategies=["range_fade", "mean_reversion", "bollinger_fade"]
        )
