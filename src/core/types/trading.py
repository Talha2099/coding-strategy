from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Literal, Dict, Optional, Any

@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(frozen=True)
class Tick:
    ts: datetime
    price: float
    size: float
    side: Literal["buy", "sell"]

@dataclass(frozen=True)
class OrderBookSnapshot:
    ts: datetime
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]

@dataclass(frozen=True)
class MicrostructureFeatures:
    spread: float
    mid_price: float
    imbalance: float
    order_flow_imbalance: float
    realized_volatility: float
    trade_intensity: float

@dataclass(frozen=True)
class TradeCandidate:
    id: str
    symbol: str
    asset_class: str
    direction: Literal["long", "short"]
    entry_zone_id: str
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_family: str
    strategy_name: str
    regime_at_entry: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    direction: Literal["long", "short"]
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float # 0.0 - 1.0
    features: Dict[str, float]
    strategy_name: str
    strategy_family: str
    regime_type: str
    timestamp: datetime
    
    def validate(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if self.direction == "long" and self.stop_loss >= self.entry_price:
            raise ValueError("Long SL must be below entry")
        if self.direction == "short" and self.stop_loss <= self.entry_price:
            raise ValueError("Short SL must be above entry")

@dataclass(frozen=True)
class RiskDecision:
    signal_id: str
    approved: bool
    size: float
    reason: str
    max_drawdown_impact: float
    timestamp: datetime
    
    def validate(self):
        if self.size < 0:
            raise ValueError("Risk size cannot be negative")

@dataclass(frozen=True)
class Action:
    type: Literal["enter", "exit", "scale_in", "scale_out", "update_stop", "cancel"]
    symbol: str
    side: str
    size: float
    price: Optional[float]
    order_type: str = "market"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class RegimeState:
    symbol: str
    regime_type: str
    lifecycle_stage: int # 0-7 as per spec
    probabilities: Dict[str, float]
    volatility: float
    trend_strength: float
    direction: int # 1 for bullish, -1 for bearish, 0 for neutral
    health_score: float = 0.5 # 0 to 1
    hurst: float = 0.5
    acceleration: float = 0.0
    overextension: float = 0.0 # Score reflecting distance from mean
    exhaustion_risk: float = 0.0 # 0 to 1
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class MTFRegimeState:
    symbol: str
    htf_state: RegimeState
    mtf_state: RegimeState
    ltf_state: RegimeState
    bias: str # "bullish", "bearish", "neutral"
    confluence_score: float # 0 to 1
    timestamp: datetime

@dataclass(frozen=True)
class ExecutionReport:
    action_id: str
    order_id: str
    status: Literal["filled", "rejected", "canceled", "partial"]
    fill_price: Optional[float]
    fill_size: float
    slippage: float
    commission: float
    venue: str
    timestamp: datetime

@dataclass(frozen=True)
class TradeLogEvent:
    event_id: str
    trade_id: str
    event_type: str # "entry", "stop_moved", "partial_exit", "close", "regime_shift"
    message: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ScoredTrade:
    candidate: TradeCandidate
    probability: float
    expected_return: float
    risk_score: float
    features: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ExecutionOrder:
    id: str
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "limit", "stop", "stop_limit"]
    price: Optional[float]
    size: float
    timestamp: datetime

@dataclass(frozen=True)
class FillResult:
    order_id: str
    fill_price: float
    fill_size: float
    slippage: float
    commission: float
    timestamp: datetime

@dataclass
class Position:
    id: str
    symbol: str
    asset_class: str
    size: float  # Positive for long, negative for short
    entry_price: float
    avg_price: float
    stop_loss: float
    take_profit: float
    entry_ts: datetime
    strategy_name: str
    regime_at_entry: Any = None
    session_at_entry: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
