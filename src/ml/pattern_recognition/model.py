import numpy as np
from typing import List, Dict
from src.core.types.trading import TradeCandidate

class PatternRecognizer:
    """
    Python implementation of Hybrid CNN-LSTM Pattern Recognition.
    Used for labeling SMC patterns with probability scores.
    """
    def __init__(self):
        self.is_ready = True

    def calculate_score(self, 
                        candidate: TradeCandidate, 
                        price_window: List[float], 
                        levels: Dict[str, float]) -> Dict[str, any]:
        """
        Infers patterns using spatial (CNN-like) and temporal (LSTM-like) proxies.
        Expanded to detect Ranging/Consolidation at levels.
        """
        if len(price_window) < 15:
            return {"score": 0.5, "label": "INSUFFICIENT_DATA"}

        prices = np.array(price_window)
        norm_prices = (prices - np.min(prices)) / (np.max(prices) - np.min(prices) + 1e-9)
        
        # 1. Ranging/Consolidation Detection (Variance-based)
        # Low volatility in the recent window relative to the overall window
        recent_window = prices[-10:]
        std_recent = np.std(recent_window)
        avg_price = np.mean(recent_window)
        cv = std_recent / avg_price if avg_price > 0 else 0
        
        is_ranging = cv < 0.001 # Threshold for tight consolidation
        
        # 2. Level Touches (Support/Resistance testing)
        entry_level = candidate.entry_zone
        touches = len([p for p in recent_window if abs(p - entry_level) / entry_level < 0.0005])
        
        # 3. V-Shape / Reversal Logic
        reversal_score = 0.0
        if norm_prices[-1] > norm_prices[-3] and norm_prices[-5] < norm_prices[-8]:
            reversal_score = 0.8 
            
        # 4. Momentum and Trend
        momentum = (price_window[-1] - price_window[-10]) / price_window[-10]
        
        # Final Scoring with Ranging Logic
        # If ranging at level, we expect a breakout. 
        # Probability depends on previous trend (Continuation) vs Reversal signals.
        base_prob = 0.5
        
        if is_ranging:
            # Consolidation logic: Often price continues in direction of momentum
            # unless a strong reversal pattern is present.
            if candidate.direction == "long":
                base_prob += 0.1 + (0.05 * touches) # Confidence grows with touches
                if momentum > 0: base_prob += 0.1 # Bullish continuation
            else:
                base_prob -= 0.1 + (0.05 * touches)
                if momentum < 0: base_prob -= 0.1
        else:
            # Mean reversion / Reversal logic
            if candidate.direction == "long":
                base_prob += (reversal_score * 0.2) + (momentum * 5.0)
            else:
                base_prob -= (reversal_score * 0.2) + (momentum * 5.0)

        prob = max(0.01, min(0.99, base_prob))
        
        return {
            "probability": prob,
            "label": self._derive_label(prob, reversal_score, is_ranging, touches),
            "features": {
                "reversal": reversal_score,
                "is_ranging": bool(is_ranging),
                "level_touches": touches,
                "volatility_cv": float(cv)
            }
        }

    def _derive_label(self, prob: float, reversal_score: float, is_ranging: bool, touches: int) -> str:
        if is_ranging:
            if touches > 3: return "MATURE_CONSOLIDATION_BREAKOUT_PENDING"
            return "LEVEL_ACCUMULATION"
        if prob > 0.8: return "STRONG_SMC_BULLISH_REVERSAL"
        if prob < 0.2: return "STRONG_SMC_BEARISH_REVERSAL"
        if reversal_score > 0.7: return "VOLATILE_SHAKE_OUT"
        return "MARKET_STRUCTURE_SHIFT"
