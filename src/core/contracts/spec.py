from enum import Enum
from typing import Dict, List, Optional
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
    commission_per_lot: float
    spread_base: float
    swap_long: float
    swap_short: float
    
    # Constraints
    allow_overnight: bool = True
    allow_short: bool = True
    
    # Session (simplified for now, UTC)
    trading_hours: Dict[str, List[str]] # e.g. {"mon": ["00:00-23:59"]}

class ContractManager:
    def __init__(self):
        self.specs: Dict[str, InstrumentSpec] = {}

    def register(self, spec: InstrumentSpec):
        self.specs[spec.symbol] = spec

    def get_spec(self, symbol: str) -> InstrumentSpec:
        if symbol not in self.specs:
            raise ValueError(f"No spec found for {symbol}")
        return self.specs[symbol]

    def get_point_pnl(self, symbol: str, size: float) -> float:
        spec = self.get_spec(symbol)
        return size * spec.point_value

    def get_session(self, dt: datetime) -> SessionType:
        # Simplified UTC Session Logic
        h = dt.hour
        if 0 <= h < 7: return SessionType.ASIA
        if 7 <= h < 12: return SessionType.LONDON
        if 12 <= h < 16: return SessionType.OVERLAP_LN_NY
        if 16 <= h < 21: return SessionType.NEW_YORK
        return SessionType.CLOSE
