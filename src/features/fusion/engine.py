from typing import Dict, Any, Optional
from src.core.types.trading import TradeCandidate, MicrostructureFeatures, RegimeState

class FeatureFusionEngine:
    """
    Unified feature engine that merges SMC structural context, 
    technical feature engineering, and optional microstructure validation.
    """
    def __init__(self):
        pass

    def build_feature_vector(self, 
                             candidate: Optional[TradeCandidate], 
                             market_features: Dict[str, float],
                             quality_metrics: Optional[Dict[str, Dict[str, float]]] = None,
                             micro: Optional[MicrostructureFeatures] = None, 
                             regime: Optional[RegimeState] = None) -> Dict[str, float]:
        """
        Combines multiple intel layers into a fixed-length feature vector for ML filtering.
        """
        features = {}
        
        # 1. Structural / Trade Parameters (If candidate provided)
        if candidate:
            entry = candidate.entry_price
            sl = candidate.stop_loss
            tp = candidate.take_profit
            
            dist_tp = abs(tp - entry)
            dist_sl = abs(sl - entry)
            
            features.update({
                "rr_ratio": dist_tp / dist_sl if dist_sl > 1e-9 else 0,
                "dist_to_tp": dist_tp,
                "dist_to_sl": dist_sl,
                "direction_val": 1.0 if candidate.direction == "long" else -1.0,
            })
        
        # 2. Market Features (from Multi-Stage Pipeline)
        features.update(market_features)
        
        # 3. Microstructure (Optional Validation)
        if micro:
            features.update({
                "micro_spread": micro.spread,
                "micro_imbalance": micro.imbalance,
                "micro_ofi": micro.order_flow_imbalance,
                "micro_rv": micro.realized_volatility,
                "micro_intensity": micro.trade_intensity
            })

        # 4. Regime State
        if regime:
            features.update({
                "regime_volatility": regime.volatility,
                "regime_trend_strength": getattr(regime, "trend_strength", 0.0),
            })
            for r_name, r_prob in regime.probabilities.items():
                features[f"regime_prob_{r_name}"] = r_prob

        # 5. Feature Quality Meta-Data (Phase 10)
        if quality_metrics:
            for f_name in ["trend_quality_score", "mean_reversion_score", "breakout_quality_score"]:
                if f_name in quality_metrics:
                    q = quality_metrics[f_name]
                    features[f"{f_name}_stability"] = q.get("stability", 1.0)
                    features[f"{f_name}_usefulness"] = q.get("usefulness", 0.5)

        return features

    def get_trade_ready_state(self, 
                             market_features: Dict[str, float],
                             quality_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Returns the complete fused state for strategy evaluation."""
        return {
            "features": market_features,
            "quality": quality_metrics,
            "status": "VALID" if len(market_features) > 10 else "INCOMPLETE",
            "timestamp_ready": True
        }
