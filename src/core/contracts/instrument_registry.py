from typing import Dict, Optional
from datetime import datetime
from src.core.contracts.instrument_spec import InstrumentSpec, SessionType
from src.core.contracts.asset_profile import AssetProfileFactory

class InstrumentRegistry:
    """Central registry mapping symbols to their behavioral and technical specs"""
    
    _registry: Dict[str, InstrumentSpec] = {}

    @classmethod
    def get_session(cls, dt: datetime, symbol: str) -> SessionType:
        """Determines the current trading session based on time and instrument hours"""
        # For now, a simplified global logic, but Phase 9 requires it to be instrument-specific
        # In a full implementation, we'd look at spec.sessions or spec.trading_hours
        h = dt.hour
        if 0 <= h < 7: return SessionType.ASIA
        if 7 <= h < 12: return SessionType.LONDON
        if 12 <= h < 16: return SessionType.LONDON # Overlap
        if 16 <= h < 21: return SessionType.NEW_YORK
        if 21 <= h < 24: return SessionType.LATE_NY
        return SessionType.ASIA # Early Asia

    @classmethod
    def register(cls, spec: InstrumentSpec):
        cls._registry[spec.symbol] = spec

    @classmethod
    def get_spec(cls, symbol: str) -> InstrumentSpec:
        if symbol not in cls._registry:
            # Fallback to intelligent guessing based on symbol naming if not registered
            cls._registry[symbol] = cls._auto_discover(symbol)
        return cls._registry[symbol]

    @classmethod
    def _auto_discover(cls, symbol: str) -> InstrumentSpec:
        """Heuristic-based profile discovery if manual spec is missing"""
        s = symbol.upper()
        # Indices
        if any(idx in s for idx in ["GER40", "US30", "NAS100", "SPX500", "UK100", "DAX", "DJI", "NDX"]):
            return AssetProfileFactory.get_index_profile(symbol)
            
        # Commodities & Gold
        elif any(comm in s for comm in ["XAU", "GOLD"]):
            return AssetProfileFactory.get_gold_profile(symbol)
        elif any(comm in s for comm in ["WTI", "BRENT", "OIL"]):
            return AssetProfileFactory.get_trend_heavy_profile(symbol) # Oil trends hard
            
        # Forex
        elif len(symbol) == 6 and any(cur in s for cur in ["EUR", "JPY", "GBP", "AUD", "NZD", "CAD", "CHF"]):
             # Most majors are mean-reverting/range-heavy
             return AssetProfileFactory.get_range_heavy_profile(symbol)
             
        # Stocks (Heuristics)
        elif "." in symbol or len(symbol) <= 4:
             # Assume high liquidity large cap for major symbols, otherwise mid/small
             if any(tkr in s for tkr in ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NVDA"]):
                  return AssetProfileFactory.get_us_large_cap_profile(symbol)
             elif "TQQQ" in s or "SQQQ" in s or "NVDA" in s:
                  return AssetProfileFactory.get_high_beta_profile(symbol)
             else:
                  return AssetProfileFactory.get_us_large_cap_profile(symbol)

        # Absolute fallback
        return AssetProfileFactory.get_forex_profile(symbol)

    @classmethod
    def is_strategy_allowed(cls, symbol: str, strategy_name: str) -> bool:
        spec = cls.get_spec(symbol)
        if strategy_name in spec.restricted_strategies:
            return False
        return True
