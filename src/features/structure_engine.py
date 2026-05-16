import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.types.trading import Candle

class StructureFeatureEngine:
    """
    STAGE C: Structural / SMC Features.
    Detects Liquidity sweeps, Fair Value Gaps (FVG), Market Structure Breaks (MSB).
    """
    
    @staticmethod
    def detect_fvg(highs: np.ndarray, lows: np.ndarray) -> np.ndarray:
        """Fair Value Gap detection (Bullish/Bearish)"""
        fvg = np.zeros_like(highs)
        if len(highs) < 3: return fvg
        
        for i in range(2, len(highs)):
            # Bullish FVG: Low of candle i > High of candle i-2
            if lows[i] > highs[i-2] and highs[i-1] > highs[i-2]:
                fvg[i] = 1.0 # Bullish gap
            # Bearish FVG: High of candle i < Low of candle i-2
            elif highs[i] < lows[i-2] and lows[i-1] < lows[i-2]:
                fvg[i] = -1.0 # Bearish gap
        return fvg

    @staticmethod
    def extract(raw_features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        if not raw_features: return {}
        
        highs = raw_features["high"]
        lows = raw_features["low"]
        closes = raw_features["close"]
        opens = raw_features["open"]
        atr = raw_features.get("atr", np.zeros_like(closes))
        
        # 1. Higher Highs / Lower Lows (Fractals)
        is_hh = np.where(highs == pd.Series(highs).rolling(20).max(), 1.0, 0.0)
        is_ll = np.where(lows == pd.Series(lows).rolling(20).min(), 1.0, 0.0)
        
        # 2. SMC: Fair Value Gaps
        fvg = StructureFeatureEngine.detect_fvg(highs, lows)
        
        # 3. Liquidity Sweeps
        # Price spikes above/below previous high/low but returns quickly (closes inside)
        max_prev = pd.Series(highs).shift(1).rolling(20).max().values
        min_prev = pd.Series(lows).shift(1).rolling(20).min().values
        
        upside_sweep = np.where((highs > max_prev) & (closes < max_prev), 1.0, 0.0)
        downside_sweep = np.where((lows < min_prev) & (closes > min_prev), 1.0, 0.0)
        
        # 4. Market Structure Breaks (MSB) and Displacement
        # Displacement: Large move (body > 1.5 ATR)
        body = np.abs(closes - opens)
        displacement = np.where(body > 1.5 * atr, 1.0, 0.0)
        
        # BOS: Break of Structure (Continuation)
        # Bullish BOS: Close > recent swing high
        # Bearish BOS: Close < recent swing low
        bos_bull = np.where((closes > max_prev) & (displacement == 1.0), 1.0, 0.0)
        bos_bear = np.where((closes < min_prev) & (displacement == 1.0), -1.0, 0.0)
        
        # CHoCH (Change of Character): First break against trend
        # Simplified: If we were in a bullish structure (HH presence) and we break a LL
        choch_bear = np.where((closes < min_prev) & (pd.Series(is_hh).rolling(50).sum() > 0), 1.0, 0.0)
        choch_bull = np.where((closes > max_prev) & (pd.Series(is_ll).rolling(50).sum() > 0), 1.0, 0.0)
        
        # 5. Order Blocks (OB) Proxy
        # Bullish OB: Last down candle before an impulsive up move
        # Bearish OB: Last up candle before an impulsive down move
        ob_bull = np.zeros_like(closes)
        ob_bear = np.zeros_like(closes)
        for i in range(1, len(closes)):
            if bos_bull[i] == 1.0:
                # Look back for the last down candle
                for j in range(i-1, max(0, i-10), -1):
                    if closes[j] < opens[j]:
                        ob_bull[j] = 1.0
                        break
            if bos_bear[i] == -1.0:
                # Look back for the last up candle
                for j in range(i-1, max(0, i-10), -1):
                    if closes[j] > opens[j]:
                        ob_bear[j] = 1.0
                        break

        # 6. Exhaustion & Acceptance
        upper_wick = highs - np.maximum(opens, closes)
        lower_wick = np.minimum(opens, closes) - lows
        total_range = highs - lows + 1e-9
        
        upper_wick_pct = upper_wick / total_range
        lower_wick_pct = lower_wick / total_range
        acceptance_high = pd.Series((closes - lows) / total_range).rolling(10).mean().values
        
        return {
            "is_hh": is_hh,
            "is_ll": is_ll,
            "fvg": fvg,
            "upside_sweep": upside_sweep,
            "downside_sweep": downside_sweep,
            "bos": bos_bull + bos_bear,
            "choch_bull": choch_bull,
            "choch_bear": choch_bear,
            "ob_bull": ob_bull,
            "ob_bear": ob_bear,
            "displacement": displacement,
            "upper_wick_pct": upper_wick_pct,
            "lower_wick_pct": lower_wick_pct,
            "acceptance_high": acceptance_high
        }
