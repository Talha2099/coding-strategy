from src.core.types.trading import ScoredTrade

class RiskEngine:
    def __init__(self, max_exposure: float = 0.02, min_prob_threshold: float = 0.6):
        self.max_exposure = max_exposure
        self.min_prob_threshold = min_prob_threshold

    def validate(self, trade: ScoredTrade) -> bool:
        """
        Gates trades based on probability and risk/reward dynamics.
        """
        # Gating based on Meta-Model probability
        if trade.probability < self.min_prob_threshold:
            return False
            
        # Gating based on Risk Score (heuristic)
        if trade.risk_score > 0.8: # Example threshold
            return False
            
        return True

    def position_size(self, trade: ScoredTrade) -> float:
        """
        Kelly-style or fixed-fraction sizing based on probability.
        """
        if not self.validate(trade):
            return 0.0
            
        # Simplified fractional sizing
        # base_size * (prob - (1-prob)/rr)
        return self.max_exposure * 100000 # Placeholder for 1 lot on 100k account
