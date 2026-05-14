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
        # HTF: 50% weight, MTF: 30% weight, LTF: 20% weight
        weighted_score = (htf_state.direction * 0.5) + (mtf_state.direction * 0.3) + (ltf_state.direction * 0.2)
        
        bias = "neutral"
        if weighted_score > 0.3: bias = "bullish"
        elif weighted_score < -0.3: bias = "bearish"
        
        # 2. Confluence Score
        # Max possible alignment is 1.0
        confluence = abs(weighted_score)
        
        # 3. Detect Structural Conflicts
        # Pullback detection: HTF is trending, but LTF/MTF are counter-trending
        is_htf_trending = htf_state.trend_strength > 25
        is_pullback = False
        if is_htf_trending:
            if htf_state.direction == 1 and ltf_state.direction == -1:
                is_pullback = True
            elif htf_state.direction == -1 and ltf_state.direction == 1:
                is_pullback = True
        
        return MTFRegimeState(
            symbol=symbol,
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
            bias=bias,
            confluence_score=confluence,
            timestamp=ltf_candles[-1].ts if ltf_candles else datetime.utcnow()
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
