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
                             candidate: TradeCandidate, 
                             technical_features: Dict[str, float],
                             micro: Optional[MicrostructureFeatures] = None, 
                             regime: Optional[RegimeState] = None) -> Dict[str, float]:
        """
        Combines multiple intel layers into a fixed-length feature vector for ML filtering.
        """
        # 1. Structural / Trade Parameters
        entry = candidate.entry_price
        sl = candidate.stop_loss
        tp = candidate.take_profit
        
        dist_tp = abs(tp - entry)
        dist_sl = abs(sl - entry)
        
        features = {
            "rr_ratio": dist_tp / dist_sl if dist_sl > 1e-9 else 0,
            "dist_to_tp": dist_tp,
            "dist_to_sl": dist_sl,
            "direction_val": 1.0 if candidate.direction == "long" else -1.0,
        }
        
        # 2. Technical Features (from TechnicalFeatureEngine)
        # We assume the caller passes a subset of scalar features for the current timestamp
        features.update(technical_features)
        
        # 3. Microstructure (Optional Validation)
        if micro:
            features.update({
                "micro_spread": micro.spread,
                "micro_imbalance": micro.imbalance,
                "micro_ofi": micro.order_flow_imbalance,
                "micro_rv": micro.realized_volatility,
                "micro_intensity": micro.trade_intensity
            })
        else:
            # Fill with neutral values if micro is not available
            features.update({
                "micro_spread": 0.0,
                "micro_imbalance": 0.0,
                "micro_ofi": 0.0,
                "micro_rv": 0.0,
                "micro_intensity": 0.0
            })

        # 4. Regime State
        if regime:
            features.update({
                "regime_volatility": regime.volatility,
                "regime_trend_strength": regime.trend_strength,
            })
            # Add probabilities as flat features
            for r_name, r_prob in regime.probabilities.items():
                features[f"regime_prob_{r_name}"] = r_prob
        else:
            features.update({
                "regime_volatility": 0.0,
                "regime_trend_strength": 0.0,
            })

        return features
