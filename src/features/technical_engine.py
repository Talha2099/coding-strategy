import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from src.core.types.trading import Candle

class TechnicalFeatureEngine:
    """
    Computes deterministic technical features for strategy logic.
    Strictly price/volume based.
    """
    @staticmethod
    def sma(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).rolling(window=window).mean().values

    @staticmethod
    def ema(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).ewm(span=window, adjust=False).mean().values

    @staticmethod
    def rsi(prices: np.ndarray, window: int = 14) -> np.ndarray:
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).values

    @staticmethod
    def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, window: int = 14) -> np.ndarray:
        tr1 = highs - lows
        tr2 = np.abs(highs - np.roll(closes, 1))
        tr3 = np.abs(lows - np.roll(closes, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return pd.Series(tr).rolling(window=window).mean().values

    @staticmethod
    def bollinger_bands(prices: np.ndarray, window: int = 20, num_std: float = 2.0) -> Dict[str, np.ndarray]:
        sma = pd.Series(prices).rolling(window=window).mean()
        std = pd.Series(prices).rolling(window=window).std()
        return {
            "upper": (sma + num_std * std).values,
            "lower": (sma - num_std * std).values,
            "mid": sma.values
        }

    @staticmethod
    def donchian_channels(highs: np.ndarray, lows: np.ndarray, window: int = 20) -> Dict[str, np.ndarray]:
        return {
            "upper": pd.Series(highs).rolling(window=window).max().values,
            "lower": pd.Series(lows).rolling(window=window).min().values,
            "mid": ((pd.Series(highs).rolling(window=window).max() + pd.Series(lows).rolling(window=window).min()) / 2).values
        }

    @staticmethod
    def vwap(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        # Simplified intra-window VWAP
        return (np.cumsum(prices * volumes) / np.cumsum(volumes))

    @staticmethod
    def zscore(prices: np.ndarray, window: int = 20) -> np.ndarray:
        sma = pd.Series(prices).rolling(window=window).mean()
        std = pd.Series(prices).rolling(window=window).std()
        return ((pd.Series(prices) - sma) / std).values

    @staticmethod
    def get_candle_features(candles: List[Candle]) -> Dict[str, np.ndarray]:
        if not candles: return {}
        df = pd.DataFrame([c.__dict__ for c in candles])
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values
        
        atr = TechnicalFeatureEngine.atr(highs, lows, closes)
        rsi = TechnicalFeatureEngine.rsi(closes)
        bb = TechnicalFeatureEngine.bollinger_bands(closes)
        donchian = TechnicalFeatureEngine.donchian_channels(highs, lows)
        
        return {
            "close": closes,
            "sma_20": TechnicalFeatureEngine.sma(closes, 20),
            "sma_50": TechnicalFeatureEngine.sma(closes, 50),
            "ema_10": TechnicalFeatureEngine.ema(closes, 10),
            "atr": atr,
            "rsi": rsi,
            "bb_upper": bb["upper"],
            "bb_lower": bb["lower"],
            "donchian_upper": donchian["upper"],
            "donchian_lower": donchian["lower"],
            "vwap": TechnicalFeatureEngine.vwap(closes, volumes),
            "zscore": TechnicalFeatureEngine.zscore(closes)
        }
