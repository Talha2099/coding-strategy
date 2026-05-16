import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from src.core.types.trading import Candle
from src.core.contracts.instrument_registry import InstrumentRegistry

class TechnicalFeatureEngine:
    """
    Computes deterministic technical features for strategy logic.
    Strictly causal price/volume based features.
    """
    @staticmethod
    def sma(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).rolling(window=window).mean().values

    @staticmethod
    def std(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).rolling(window=window).std().values

    @staticmethod
    def zscore(prices: np.ndarray, window: int) -> np.ndarray:
        sma = TechnicalFeatureEngine.sma(prices, window)
        std = TechnicalFeatureEngine.std(prices, window)
        return (prices - sma) / (std + 1e-9)

    @staticmethod
    def ema(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).ewm(span=window, adjust=False).mean().values

    @staticmethod
    def rsi(prices: np.ndarray, window: int = 14) -> np.ndarray:
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return (100 - (100 / (1 + rs))).values

    @staticmethod
    def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, window: int = 14) -> np.ndarray:
        tr1 = highs - lows
        tr2 = np.abs(highs - np.roll(closes, 1))
        tr3 = np.abs(lows - np.roll(closes, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = tr[1] if len(tr) > 1 else 0
        return pd.Series(tr).rolling(window=window).mean().values

    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
        fast_ema = TechnicalFeatureEngine.ema(prices, fast)
        slow_ema = TechnicalFeatureEngine.ema(prices, slow)
        macd_line = fast_ema - slow_ema
        signal_line = pd.Series(macd_line).ewm(span=signal, adjust=False).mean().values
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": macd_line - signal_line
        }

    @staticmethod
    def adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, window: int = 14) -> np.ndarray:
        plus_dm = pd.Series(highs).diff()
        minus_dm = pd.Series(lows).diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = -minus_dm
        atr = TechnicalFeatureEngine.atr(highs, lows, closes, window)
        plus_di = 100 * (pd.Series(plus_dm).rolling(window).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window).mean() / atr)
        dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
        return pd.Series(dx).rolling(window).mean().values

    @staticmethod
    def slope(series: np.ndarray, window: int = 5) -> np.ndarray:
        y = series
        def calc_slope(y_window):
            if np.any(np.isnan(y_window)): return 0.0
            x_window = np.arange(len(y_window))
            slope, _ = np.polyfit(x_window, y_window, 1)
            return slope
        return pd.Series(y).rolling(window=window).apply(calc_slope).values

    @staticmethod
    def hurst_exponent(prices: np.ndarray, window: int = 100) -> float:
        if len(prices) < window: return 0.5
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    @staticmethod
    def get_candle_stats(highs, lows, opens, closes) -> Dict[str, np.ndarray]:
        body = np.abs(closes - opens)
        upper_wick = highs - np.maximum(opens, closes)
        lower_wick = np.minimum(opens, closes) - lows
        total_range = highs - lows
        return {
            "body_pct": body / (total_range + 1e-9),
            "upper_wick_pct": upper_wick / (total_range + 1e-9),
            "lower_wick_pct": lower_wick / (total_range + 1e-9),
            "range": total_range
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
        return (np.cumsum(prices * volumes) / (np.cumsum(volumes) + 1e-9))

    @staticmethod
    def get_candle_features(candles: List[Candle], symbol: Optional[str] = None) -> Dict[str, np.ndarray]:
        if len(candles) < 2: return {}
        
        from src.features.pipeline import FeaturePipeline
        from src.regime.engine import RegimeEngine
        
        # 1. Pipeline instance
        pipeline = FeaturePipeline()
        
        # 2. Get Regime if possible
        regime_state = None
        if len(candles) >= 50:
            regime_engine = RegimeEngine()
            regime_state = regime_engine.classify(candles, symbol or "UNKNOWN")
            
        # 3. Generate Multi-Stage Features
        features = pipeline.generate_market_state(candles, regime_state)
        
        # 4. Instrument Context (Phase 11 legacy support)
        if symbol:
            spec = InstrumentRegistry.get_spec(symbol)
            if spec:
                closes = features["close"]
                features["instrument_profile"] = np.full_like(closes, spec.behavior.archetype.value, dtype=object)
                features["asset_class"] = np.full_like(closes, spec.asset_class.value, dtype=object)
                features["news_sensitivity"] = np.full_like(closes, float(spec.behavior.news_sensitivity))
                features["trend_persistence"] = np.full_like(closes, float(spec.behavior.trend_persistence))
                features["mean_reversion_propensity"] = np.full_like(closes, float(spec.behavior.mean_reversion_propensity))
                features["gap_frequency_factor"] = np.full_like(closes, float(spec.behavior.gap_frequency))
                features["execution_cost_fixed"] = np.full_like(closes, float(spec.cost_model.spread_fixed))
        
        return features
