from pydantic import BaseModel
from typing import Dict

class RiskConfig(BaseModel):
    max_exposure: float = 0.02
    min_prob: float = 0.6

class AppConfig(BaseModel):
    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    risk: RiskConfig = RiskConfig()
    ml_enabled: bool = True
