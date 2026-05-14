from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from src.core.types.trading import Candle, Tick, RegimeState, MTFRegimeState
from src.core.types.strategy import TradeIdea, RegimeType, StrategyFamily
from src.core.contracts.spec import InstrumentSpec

class BaseStrategy(ABC):
    def __init__(self, name: str, family: StrategyFamily, spec: InstrumentSpec):
        self.name = name
        self.family = family
        self.spec = spec

    @abstractmethod
    def is_valid_regime(self, regime: RegimeType) -> bool:
        """Determines if the strategy should even look for setups in this regime."""
        pass

    @abstractmethod
    def detect_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> bool:
        """Initial signal scan for a potential setup."""
        pass

    @abstractmethod
    def confirm_entry(self, candles: List[Candle]) -> bool:
        """Secondary confirmation (e.g. candle close, retest, momentum)."""
        pass

    @abstractmethod
    def define_stop(self, candles: List[Candle]) -> float:
        """Calculates the stop loss price."""
        pass

    @abstractmethod
    def define_target(self, candles: List[Candle]) -> float:
        """Calculates the take profit price."""
        pass

    @abstractmethod
    def score_setup(self, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> float:
        """Scores the quality of the setup (0.0 to 1.0)."""
        pass

    def on_trade_update(self, candles: List[Candle], idea: TradeIdea, regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[Dict]:
        """
        Optional hook to monitor active trades.
        Can suggest stop adjustments or early exits.
        Returns a dict of updates (e.g. {'stop_loss': 123.4, 'exit': True})
        """
        return None

    @abstractmethod
    def build_trade_idea(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> Optional[TradeIdea]:
        """Assembles the final TradeIdea object."""
        pass
