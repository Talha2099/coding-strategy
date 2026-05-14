from typing import Dict, List, Optional
from datetime import datetime
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import RegimeType
from src.regime.engine import RegimeEngine

class MTFRegimeEngine:
    """
    Synchronizes across multiple timeframes to provide a unified market bias.
    HTF: Primary Trend Bias
    MTF: Setup Validation / Structural Context
    LTF: Precise Entry Momentum
    """
    def __init__(self):
        self.engine = RegimeEngine()

    def analyze(self, candle_map: Dict[str, List[Candle]], symbol: str) -> MTFRegimeState:
        """
        Expects candle_map with "HTF", "MTF", "LTF" keys.
        """
        htf_candles = candle_map.get("HTF", [])
        mtf_candles = candle_map.get("MTF", [])
        ltf_candles = candle_map.get("LTF", [])
        
        htf_state = self.engine.classify(htf_candles, symbol)
        mtf_state = self.engine.classify(mtf_candles, symbol)
        ltf_state = self.engine.classify(ltf_candles, symbol)
        
        # 1. Calculate Multi-Timeframe Bias
        # HTF is the anchor: 60%, MTF: 25%, LTF: 15%
        weighted_score = (htf_state.direction * 0.6) + (mtf_state.direction * 0.25) + (ltf_state.direction * 0.15)
        
        bias = "neutral"
        if weighted_score > 0.4: bias = "bullish"
        elif weighted_score < -0.4: bias = "bearish"
        
        # 2. Confluence Score
        confluence = abs(weighted_score)
        
        # 3. Detect Structural Context & Conflicts
        # Pullback: HTF is strong trend, but MTF/LTF are correcting
        is_pullback = False
        is_noise = False
        htf_trending = htf_state.trend_strength > 30 and htf_state.health_score > 0.5
        
        if htf_trending:
            # Pullback if MTF direction != HTF direction
            if htf_state.direction != mtf_state.direction and mtf_state.direction != 0:
                is_pullback = True
            # Noise if LTF is oscillating but MTF/HTF are stable
            elif ltf_state.trend_strength < 20 and mtf_state.direction == htf_state.direction:
                is_noise = True

        # HTF Weakening check
        htf_weakening = htf_state.acceleration < 0 and htf_state.exhaustion_risk > 0.6
        
        return MTFRegimeState(
            symbol=symbol,
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
            bias=bias,
            confluence_score=confluence,
            timestamp=ltf_candles[-1].ts if ltf_candles else datetime.utcnow(),
            metadata={
                "is_pullback": is_pullback,
                "is_noise": is_noise,
                "htf_weakening": htf_weakening,
                "weighted_score": weighted_score
            }
        )

    def is_aligned(self, mtf_state: MTFRegimeState, direction: str) -> bool:
        """
        Checks if a trade direction is aligned with the multi-timeframe bias.
        """
        dir_val = 1 if direction == "long" else -1
        
        # Strong alignment: HTF and Bias must agree with trade direction
        if mtf_state.bias == "neutral":
             return False
             
        bias_val = 1 if mtf_state.bias == "bullish" else -1
        
        # Mandatory: Bias must match trade direction
        if bias_val != dir_val:
            return False
            
        # Optional: HTF must match trade direction for high conviction
        if mtf_state.htf_state.direction != dir_val and mtf_state.htf_state.direction != 0:
            return False
            
        return True
