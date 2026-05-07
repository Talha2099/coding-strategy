from typing import List, Dict, Type
from src.strategies.base import BaseStrategy
from src.core.types.strategy import RegimeType, StrategyFamily, TradeIdea
from src.core.types.trading import Candle

class StrategyRouter:
    """
    Routes incoming data to active strategies based on regime.
    Aggregates trade ideas.
    """
    def __init__(self):
        self.strategies: List[BaseStrategy] = []

    def register_strategy(self, strategy: BaseStrategy):
        self.strategies.append(strategy)

    def get_trade_ideas(self, symbol: str, candles: List[Candle], regime: RegimeType) -> List[TradeIdea]:
        ideas = []
        for strategy in self.strategies:
            if strategy.is_valid_regime(regime):
                if strategy.detect_setup(candles, regime):
                    idea = strategy.build_trade_idea(symbol, candles, regime)
                    if idea:
                        ideas.append(idea)
        return ideas
