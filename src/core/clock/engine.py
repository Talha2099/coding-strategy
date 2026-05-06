from datetime import datetime
import pytz

class QuantClock:
    """
    Unified clock for backtesting and live execution.
    """
    def __init__(self, mode: str = "live"):
        self.mode = mode
        self._backtest_time = None

    def now(self) -> datetime:
        if self.mode == "live":
            return datetime.now(pytz.UTC)
        return self._backtest_time

    def set_time(self, ts: datetime):
        if self.mode == "backtest":
            self._backtest_time = ts
