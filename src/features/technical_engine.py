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
        
        spec = InstrumentRegistry.get_spec(symbol) if symbol else None
        
        df = pd.DataFrame([c.__dict__ for c in candles])
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        opens = df['open'].values
        volumes = df['volume'].values
        timestamps = df['ts'].values

        rel_vol = volumes / (pd.Series(volumes).rolling(window=20).mean().values + 1e-9)
        log_returns = np.log(closes / (pd.Series(closes).shift(1).values + 1e-9))
        log_returns[0] = 0
        returns = pd.Series(closes).pct_change().fillna(0).values
        realized_vol = pd.Series(log_returns).rolling(window=14).std().values * np.sqrt(252 * 1440) 
        atr = TechnicalFeatureEngine.atr(highs, lows, closes, 14)
        
        sma_20 = TechnicalFeatureEngine.sma(closes, 20)
        sma_50 = TechnicalFeatureEngine.sma(closes, 50)
        ema_20 = TechnicalFeatureEngine.ema(closes, 20)
        ema_50 = TechnicalFeatureEngine.ema(closes, 50)
        ema_200 = TechnicalFeatureEngine.ema(closes, 200)
        
        sma_20_slope = TechnicalFeatureEngine.slope(sma_20, 5)
        sma_20_curve = TechnicalFeatureEngine.slope(sma_20_slope, 5) 
        
        ema_cross = np.where(ema_20 > ema_50, 1.0, -1.0)
        ema_cross_golden = np.where((ema_50 > ema_200) & (ema_20 > ema_50), 1.0, 0.0)
        
        vwap_val = TechnicalFeatureEngine.vwap(closes, volumes)
        vwap_dist = (closes - vwap_val) / (closes + 1e-9)

        rsi = TechnicalFeatureEngine.rsi(closes, 14)
        macd = TechnicalFeatureEngine.macd(closes)
        adx = TechnicalFeatureEngine.adx(highs, lows, closes, 14)
        zscore = TechnicalFeatureEngine.zscore(closes, 20)
        
        bb_mid = pd.Series(closes).rolling(20).mean()
        bb_std = pd.Series(closes).rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / (bb_mid + 1e-9)
        bb_squeeze = np.where(bb_width < pd.Series(bb_width).rolling(100).min().shift(1) * 1.1, 1.0, 0.0)
        bb_expansion = pd.Series(bb_width).diff().values
        
        donchian = TechnicalFeatureEngine.donchian_channels(highs, lows, 20)
        breakout_dist_upper = (highs - donchian["upper"]) / (atr + 1e-9)
        breakout_dist_lower = (lows - donchian["lower"]) / (atr + 1e-9)
        range_width = (donchian["upper"] - donchian["lower"]) / (sma_20 + 1e-9)

        is_hh = np.where(highs == pd.Series(highs).rolling(20).max(), 1.0, 0.0)
        is_ll = np.where(lows == pd.Series(lows).rolling(20).min(), 1.0, 0.0)
        
        h_val = TechnicalFeatureEngine.hurst_exponent(closes, 100)
        hurst = np.full_like(closes, float(h_val))
        net_dist = np.abs(closes - pd.Series(closes).shift(20).values)
        path_len = pd.Series(np.abs(np.diff(closes, prepend=closes[0]))).rolling(20).sum().values
        efficiency = net_dist / (path_len + 1e-9) 

        prev_close = pd.Series(closes).shift(1).values
        gap_size = (opens - prev_close) / (prev_close + 1e-9)
        
        def _get_session_val(ts):
            h = pd.to_datetime(ts).hour
            if 0 <= h < 7: return 1 
            if 7 <= h < 12: return 2
            if 12 <= h < 16: return 3 
            if 16 <= h < 21: return 4 
            return 0 
        session_labels = np.array([_get_session_val(ts) for ts in timestamps])

        dist_ema20 = (closes - ema_20) / (atr + 1e-9)
        exhaustion_score = np.where((np.abs(dist_ema20) > 4.0) & (rel_vol > 2.0) & ((rsi > 80) | (rsi < 20)), 1.0, 0.0)
        
        candle_pct = (closes - lows) / (highs - lows + 1e-9)
        acceptance_high = pd.Series(candle_pct).rolling(10).mean().values
        
        max_high = pd.Series(highs).rolling(20).max()
        min_low = pd.Series(lows).rolling(20).min()
        pullback_depth_bull = (max_high - closes) / (atr + 1e-9)
        pullback_depth_bear = (closes - min_low) / (atr + 1e-9)
        
        vol_ma = pd.Series(realized_vol).rolling(50).mean()
        vol_regime = np.where(realized_vol > vol_ma * 1.5, 2.0, np.where(realized_vol < vol_ma * 0.7, 0.0, 1.0)) 

        c_stats = TechnicalFeatureEngine.get_candle_stats(highs, lows, opens, closes)
        
        # Base result
        features = {
            "close": closes,
            "high": highs,
            "low": lows,
            "open": opens,
            "volume": volumes,
            "rel_vol": rel_vol,
            "log_returns": log_returns,
            "returns": returns,
            "realized_vol": realized_vol,
            "vol_regime": vol_regime,
            "atr": atr,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "sma_20_slope": sma_20_slope,
            "sma_20_curve": sma_20_curve,
            "ema_cross": ema_cross,
            "ema_cross_golden": ema_cross_golden,
            "vwap_dist": vwap_dist,
            "rsi": rsi,
            "zscore": zscore,
            "macd": macd["macd"],
            "macd_hist": macd["histogram"],
            "adx": adx,
            "bb_width": bb_width.values,
            "bb_upper": bb_upper.values,
            "bb_lower": bb_lower.values,
            "bb_squeeze": bb_squeeze,
            "bb_expansion": bb_expansion,
            "breakout_dist_upper": breakout_dist_upper,
            "breakout_dist_lower": breakout_dist_lower,
            "range_width": range_width,
            "is_hh": is_hh,
            "is_ll": is_ll,
            "efficiency": efficiency,
            "hurst": hurst,
            "gap_size": gap_size,
            "session_labels": session_labels,
            "exhaustion_score": exhaustion_score,
            "dist_ema20": dist_ema20,
            "acceptance_high": acceptance_high,
            "pullback_depth_bull": pullback_depth_bull.values,
            "pullback_depth_bear": pullback_depth_bear.values,
            "body_pct": c_stats["body_pct"],
            "upper_wick_pct": c_stats["upper_wick_pct"],
            "lower_wick_pct": c_stats["lower_wick_pct"],
            "candle_range": c_stats["range"]
        }

        # PHASE 13: Behavioral Scores Integration
        # Calculate scores for logging and feature use (Vectorized replacements for BehaviorEngine)
        h_score_vec = np.clip((hurst - 0.5) / 0.3, 0, 1)
        adx_score_vec = np.clip((adx - 20) / 40, 0, 1)
        eff_score_vec = np.clip(efficiency / 0.8, 0, 1)
        features["trend_score_dynamic"] = 0.4 * h_score_vec + 0.3 * adx_score_vec + 0.3 * eff_score_vec
        
        mr_h_score = np.clip((0.5 - hurst) / 0.3, 0, 1)
        mr_z_score = np.clip((np.abs(zscore) - 1.5) / 1.5, 0, 1)
        mr_bb_score = 1.0 - np.clip(bb_expansion * 10, 0, 1)
        features["mean_reversion_score_dynamic"] = 0.4 * mr_h_score + 0.4 * mr_z_score + 0.2 * mr_bb_score
        
        vol_score_vec = np.clip((rel_vol - 1.2) / 2.0, 0, 1)
        features["breakout_score_dynamic"] = 0.4 * vol_score_vec + 0.3 * bb_squeeze + 0.3 * np.clip((returns * closes) / (atr + 1e-9), 0, 1)
        
        max_wick = np.maximum(c_stats["upper_wick_pct"], c_stats["lower_wick_pct"])
        wick_score_vec = np.clip((max_wick - 0.3) / 0.4, 0, 1)
        fake_vol_score = 1.0 - np.clip(rel_vol / 1.5, 0, 1)
        overextended_score = np.clip((np.abs(zscore) - 2.5) / 1.5, 0, 1)
        features["fake_breakout_prob_dynamic"] = 0.5 * wick_score_vec + 0.2 * fake_vol_score + 0.3 * overextended_score

        # PHASE 11: INSTRUMENT CONTEXT IN FEATURE ENGINE
        if spec:
            features["instrument_profile"] = np.full_like(closes, spec.behavior.archetype.value, dtype=object)
            features["asset_class"] = np.full_like(closes, spec.asset_class.value, dtype=object)
            features["news_sensitivity"] = np.full_like(closes, float(spec.behavior.news_sensitivity))
            features["trend_persistence"] = np.full_like(closes, float(spec.behavior.trend_persistence))
            features["mean_reversion_propensity"] = np.full_like(closes, float(spec.behavior.mean_reversion_propensity))
            features["gap_frequency_factor"] = np.full_like(closes, float(spec.behavior.gap_frequency))
            features["holding_cost_bps"] = np.full_like(closes, float(spec.cost_model.swap_long)) 
            features["execution_cost_fixed"] = np.full_like(closes, float(spec.cost_model.spread_fixed))
            features["partial_fill_likelihood"] = np.full_like(closes, float(spec.cost_model.partial_fill_likelihood))
            features["event_risk_sensitivity"] = np.full_like(closes, float(spec.behavior.event_risk_sensitivity))
            features["liquidity_context"] = np.full_like(closes, spec.point_value) # Using point value as a proxy or just spec info
        
        return features
