from typing import List, Dict, Type, Optional
from src.strategies.base import BaseStrategy
from src.core.types.strategy import RegimeType, StrategyFamily, TradeIdea
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.contracts.spec import ContractManager

class StrategyRouter:
    """
    Advanced router that activates strategies based on regime, session, and asset class.
    Ranks ideas and suppresses conflicting signals.
    """
    def __init__(self, contract_manager: ContractManager):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.contract_manager = contract_manager

    def register_strategy(self, strategy: BaseStrategy):
        self.strategies[strategy.name] = strategy

    def get_trade_ideas(self, symbol: str, candles: List[Candle], regime_state: RegimeState, mtf_state: Optional[MTFRegimeState] = None) -> List[TradeIdea]:
        if not candles:
            return []
            
        ideas = []
        spec = self.contract_manager.get_spec(symbol)
        session = self.contract_manager.get_session(candles[-1].ts)
        regime = RegimeType(regime_state.regime_type)
        
        # 1. Collect potential ideas from valid strategies
        for name, strategy in self.strategies.items():
            # Check regime validity
            if not strategy.is_valid_regime(regime):
                continue
                
            # Detect setup
            if strategy.detect_setup(candles, regime_state, mtf_state):
                # Confirm entry
                if strategy.confirm_entry(candles):
                    idea = strategy.build_trade_idea(symbol, candles, regime_state, mtf_state)
                    if idea:
                        ideas.append(idea)
        
        # 2. Sort/Rank by expectancy (Confidence * RR)
        ideas.sort(key=lambda x: x.confidence_score * x.risk_reward_ratio, reverse=True)
        
        # 3. Suppress conflicting signals for the same symbol
        final_ideas = []
        seen_symbols = set()
        for idea in ideas:
            if idea.symbol not in seen_symbols:
                final_ideas.append(idea)
                seen_symbols.add(idea.symbol)
        
        return final_ideas
