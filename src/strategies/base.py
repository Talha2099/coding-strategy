from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from src.core.types.trading import Candle, Tick
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.contracts.spec import InstrumentSpec

class BaseStrategy(ABC):
    def __init__(self, name: str, family: StrategyFamily, spec: InstrumentSpec):
        self.name = name
        self.family = family
        self.spec = spec

    @abstractmethod
    def detect_setup(self, candles: List[Candle], regime: RegimeType) -> bool:
        """Initial signal scan."""
        pass

    @abstractmethod
    def build_trade_idea(self, symbol: str, candles: List[Candle], regime: RegimeType) -> Optional[TradeIdea]:
        """Calculates entry, stop, and target."""
        pass

    def is_valid_regime(self, regime: RegimeType) -> bool:
        """Default filter: strategy only runs in its intended regime."""
        return regime.value.startswith(self.family.value) or regime == RegimeType.TRENDING_BULL or regime == RegimeType.TRENDING_BEAR
