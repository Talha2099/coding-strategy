import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from src.core.types.trading import Candle

class RawFeatureEngine:
    """
    STAGE A: Raw Technical Feature Extraction.
    Calculates primary indicators and basic price-action metrics.
    Strictly causal.
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
        rs = gain / (loss + 1e-9)
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
    def bollinger_bands(prices: np.ndarray, window: int = 20, num_std: float = 2.0) -> Dict[str, np.ndarray]:
        mid = RawFeatureEngine.sma(prices, window)
        std = pd.Series(prices).rolling(window=window).std().values
        return {
            "upper": mid + num_std * std,
            "mid": mid,
            "lower": mid - num_std * std,
            "bandwidth": (2 * num_std * std) / (mid + 1e-9)
        }

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
    def hurst_exponent(prices: np.ndarray, window: int = 100) -> np.ndarray:
        """Hurst exponent calculated on a rolling window."""
        results = np.full_like(prices, 0.5)
        if len(prices) < window: return results
        
        def _calc_hurst(p):
            if len(p) < 20: return 0.5
            lags = range(2, 20)
            tau = [np.sqrt(np.std(np.subtract(p[lag:], p[:-lag]))) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0

        results = pd.Series(prices).rolling(window=window).apply(_calc_hurst).values
        return results

    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
        fast_ema = RawFeatureEngine.ema(prices, fast)
        slow_ema = RawFeatureEngine.ema(prices, slow)
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
        atr = RawFeatureEngine.atr(highs, lows, closes, window)
        plus_di = 100 * (pd.Series(plus_dm).rolling(window).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window).mean() / atr)
        dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
        return pd.Series(dx).rolling(window).mean().values

    @staticmethod
    def vwap(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        return (np.cumsum(prices * volumes) / (np.cumsum(volumes) + 1e-9))

    @staticmethod
    def rolling_zscore(series: np.ndarray, window: int = 20) -> np.ndarray:
        s = pd.Series(series)
        mean = s.rolling(window).mean()
        std = s.rolling(window).std()
        return ((s - mean) / (std + 1e-9)).values

    @staticmethod
    def keltner_channels(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, window: int = 20, atr_mult: float = 2.0) -> Dict[str, np.ndarray]:
        mid = RawFeatureEngine.ema(closes, window)
        atr = RawFeatureEngine.atr(highs, lows, closes, window)
        return {
            "upper": mid + atr_mult * atr,
            "mid": mid,
            "lower": mid - atr_mult * atr,
            "width": (2 * atr_mult * atr) / (mid + 1e-9)
        }

    @staticmethod
    def swing_points(highs: np.ndarray, lows: np.ndarray, window: int = 5) -> Dict[str, np.ndarray]:
        """Detects swing highs and lows within a local window."""
        s_highs = np.zeros_like(highs)
        s_lows = np.zeros_like(lows)
        
        for i in range(window, len(highs) - window):
            if highs[i] == np.max(highs[i-window : i+window+1]):
                s_highs[i] = 1.0
            if lows[i] == np.min(lows[i-window : i+window+1]):
                s_lows[i] = 1.0
        return {"highs": s_highs, "lows": s_lows}

    @staticmethod
    def autocorrelation_decay(returns: np.ndarray, window: int = 20, lag: int = 1) -> np.ndarray:
        s = pd.Series(returns)
        return s.rolling(window).apply(lambda x: x.autocorr(lag=lag)).values

    @staticmethod
    def volatility_clustering(log_returns: np.ndarray, window: int = 20) -> np.ndarray:
        """Proxy: Autocorrelation of absolute returns."""
        abs_ret = np.abs(log_returns)
        return RawFeatureEngine.autocorrelation_decay(abs_ret, window, lag=1)

    @staticmethod
    def time_in_trend(ema_cross: np.ndarray) -> np.ndarray:
        """Counts how many bars the EMA cross has been in the current state."""
        counts = np.zeros_like(ema_cross)
        current_count = 0
        for i in range(1, len(ema_cross)):
            if ema_cross[i] == ema_cross[i-1]:
                current_count += 1
            else:
                current_count = 0
            counts[i] = current_count
        return counts

    @staticmethod
    def extract(candles: List[Candle]) -> Dict[str, np.ndarray]:
        if not candles: return {}
        
        df = pd.DataFrame([c.__dict__ for c in candles])
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        opens = df['open'].values
        volumes = df['volume'].values
        
        # A. Price / Return Structure
        returns = pd.Series(closes).pct_change().fillna(0).values
        log_returns = np.log(closes / (pd.Series(closes).shift(1).values + 1e-9))
        log_returns[0] = 0
        cum_returns = np.cumsum(log_returns)
        
        range_val = highs - lows
        body_val = np.abs(closes - opens)
        upper_wick = highs - np.maximum(opens, closes)
        lower_wick = np.minimum(opens, closes) - lows
        
        body_pct = body_val / (range_val + 1e-9)
        upper_wick_pct = upper_wick / (range_val + 1e-9)
        lower_wick_pct = lower_wick / (range_val + 1e-9)
        
        # Close Location Value (CLV): [(close-low)-(high-close)]/(high-low)
        clv = ((closes - lows) - (highs - closes)) / (range_val + 1e-9)
        
        # B. Trend / Momentum
        atr = RawFeatureEngine.atr(highs, lows, closes, 14)
        rsi = RawFeatureEngine.rsi(closes, 14)
        ema_20 = RawFeatureEngine.ema(closes, 20)
        ema_50 = RawFeatureEngine.ema(closes, 50)
        ema_200 = RawFeatureEngine.ema(closes, 200)
        
        slope_20 = RawFeatureEngine.slope(ema_20, 5)
        acceleration_20 = RawFeatureEngine.slope(slope_20, 5)
        
        dist_ema20 = (closes - ema_20) / (atr + 1e-9)
        dist_ema50 = (closes - ema_50) / (atr + 1e-9)
        ema_cross = np.where(ema_20 > ema_50, 1.0, -1.0)
        
        # C. Volatility / Range
        bb = RawFeatureEngine.bollinger_bands(closes, 20)
        kc = RawFeatureEngine.keltner_channels(highs, lows, closes, 20)
        bb_width = bb["bandwidth"]
        bb_squeeze = np.where(bb_width < pd.Series(bb_width).rolling(100).min().shift(1) * 1.1, 1.0, 0.0)
        
        vol_p75 = pd.Series(atr).rolling(100).quantile(0.75).values
        vol_p25 = pd.Series(atr).rolling(100).quantile(0.25).values
        vol_percentile = (atr - vol_p25) / (vol_p75 - vol_p25 + 1e-9)
        
        # D. Mean Reversion / Stretch
        zscore = RawFeatureEngine.rolling_zscore(closes, 20)
        vwap = RawFeatureEngine.vwap(closes, volumes)
        vwap_dist = (closes - vwap) / (atr + 1e-9)
        
        # E. Swing / Structure
        swings = RawFeatureEngine.swing_points(highs, lows, 5)
        is_hh = np.where((swings["highs"] == 1) & (highs > pd.Series(highs).shift(1).rolling(50).max().fillna(0)), 1.0, 0.0)
        is_ll = np.where((swings["lows"] == 1) & (lows < pd.Series(lows).shift(1).rolling(50).min().fillna(1e9)), 1.0, 0.0)
        
        # Final Output Assembly
        ema_cross = np.where(ema_20 > ema_50, 1.0, -1.0)
        
        return {
            # Raw Data
            "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes,
            
            # Price / Returns
            "returns": returns,
            "log_returns": log_returns,
            "cum_returns": cum_returns,
            "body_pct": body_pct,
            "upper_wick_pct": upper_wick_pct,
            "lower_wick_pct": lower_wick_pct,
            "clv": clv,
            "true_range_pct": atr / (closes + 1e-9),
            "autocorr_returns": RawFeatureEngine.autocorrelation_decay(log_returns, 20),
            
            # Trend / Momentum
            "atr": atr,
            "rsi": rsi,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "slope_20": slope_20,
            "acceleration_20": acceleration_20,
            "dist_ema20": dist_ema20,
            "dist_ema50": dist_ema50,
            "ema_cross": ema_cross,
            "time_in_trend": RawFeatureEngine.time_in_trend(ema_cross),
            "hurst": RawFeatureEngine.hurst_exponent(closes, 100),
            "adx": RawFeatureEngine.adx(highs, lows, closes, 14),
            
            # Volatility
            "bb_upper": bb["upper"],
            "bb_mid": bb["mid"],
            "bb_lower": bb["lower"],
            "bb_width": bb_width,
            "bb_squeeze": bb_squeeze,
            "kc_upper": kc["upper"],
            "kc_lower": kc["lower"],
            "kc_width": kc["width"],
            "vol_percentile": vol_percentile,
            "vol_clustering": RawFeatureEngine.volatility_clustering(log_returns, 20),
            
            # Mean Reversion
            "zscore": zscore,
            "vwap_dist": vwap_dist,
            
            # Structure
            "swing_high": swings["highs"],
            "swing_low": swings["lows"],
            "is_hh": is_hh,
            "is_ll": is_ll
        }

