from enum import Enum
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel
from datetime import time, datetime

class AssetClass(Enum):
    CFD = "cfd"
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"

class SessionType(Enum):
    ASIA = "asia"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP_LN_NY = "overlap_ln_ny"
    CLOSE = "close"

class InstrumentSpec(BaseModel):
    symbol: str
    asset_class: AssetClass
    venue: str
    tick_size: float
    point_value: float
    contract_size: float
    min_lot: float
    lot_step: float
    base_currency: str
    leverage_max: float
    
    # Costs
    commission_per_lot: float = 0.0
    commission_type: Literal["fixed", "bps"] = "fixed"
    spread_base: float = 0.0
    swap_long: float = 0.0
    swap_short: float = 0.0
    
    # Execution Constraints
    allow_overnight: bool = True
    allow_short: bool = True
    max_position_size: Optional[float] = None
    
    # Corporate Actions (for Stocks)
    dividend_yield: Optional[float] = 0.0 
    split_ratio: Optional[float] = 1.0
    earnings_dates: Optional[List[datetime]] = []
    
    # Session (UTC range strings, e.g. "09:00-17:00")
    trading_hours: Dict[str, List[str]] = {} 
    holiday_calendar: List[str] = [] # Format: "YYYY-MM-DD"
    
    # Behavior & Risk
    gap_handling: Literal["aggressive", "conservative", "neutral"] = "neutral"
    margin_rate: float = 1.0 # 1.0 = 100% margin required (non-leaveraged)
    
    # Specific Behavior Profile Flags
    macro_session_sensitivity: bool = False
    vol_expansion_sensitivity: bool = False
    stop_widening_factor: float = 1.0 # default 1.0x
    opening_range_focus: bool = False
    gap_priority: Literal["continuation", "fill", "none"] = "none"
    earnings_aware: bool = False
    auction_aware: bool = False

class ContractManager:
    def __init__(self):
        self.specs: Dict[str, InstrumentSpec] = {}
        self.fx_rates: Dict[str, float] = {"USD": 1.0} # Base for conversions

    def register(self, spec: InstrumentSpec):
        self.specs[spec.symbol] = spec

    def get_spec(self, symbol: str) -> InstrumentSpec:
        if symbol not in self.specs:
            raise ValueError(f"No spec found for {symbol}")
        return self.specs[symbol]

    def set_fx_rate(self, currency: str, rate_to_usd: float):
        self.fx_rates[currency] = rate_to_usd

    def get_point_pnl(self, symbol: str, size: float, quote_currency: str = "USD") -> float:
        spec = self.get_spec(symbol)
        pnl_in_base = size * spec.point_value
        
        if spec.base_currency == quote_currency:
            return pnl_in_base
            
        # Conversion logic: PnL * (BaseCurrency / QuoteCurrency)
        base_rate = self.fx_rates.get(spec.base_currency, 1.0)
        quote_rate = self.fx_rates.get(quote_currency, 1.0)
        
        return pnl_in_base * (base_rate / quote_rate)

    def is_holiday(self, dt: datetime, symbol: str) -> bool:
        spec = self.get_spec(symbol)
        return dt.strftime("%Y-%m-%d") in spec.holiday_calendar

    def get_session(self, dt: datetime) -> SessionType:
        # Simplified UTC Session Logic
        h = dt.hour
        if 0 <= h < 7: return SessionType.ASIA
        if 7 <= h < 12: return SessionType.LONDON
        if 12 <= h < 16: return SessionType.OVERLAP_LN_NY
        if 16 <= h < 21: return SessionType.NEW_YORK
        return SessionType.CLOSE
