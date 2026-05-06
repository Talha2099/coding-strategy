from typing import Dict
from src.core.types.trading import TradeCandidate, MicrostructureFeatures

class FeatureFusionEngine:
    def __init__(self):
        pass

    def build_feature_vector(self, 
                             candidate: TradeCandidate, 
                             micro: MicrostructureFeatures, 
                             market_state: Dict) -> Dict[str, float]:
        """
        Combines SMC signals, market regime, and microstructure state.
        """
        features = {
            "entry_zone": candidate.entry_zone,
            "dist_to_tp": abs(candidate.take_profit - candidate.entry_zone),
            "dist_to_sl": abs(candidate.stop_loss - candidate.entry_zone),
            "rr_ratio": abs(candidate.take_profit - candidate.entry_zone) / abs(candidate.stop_loss - candidate.entry_zone) if abs(candidate.stop_loss - candidate.entry_zone) > 0 else 0,
            
            # Microstructure
            "spread": micro.spread,
            "depth_imbalance": micro.imbalance,
            "ofi": micro.order_flow_imbalance,
            "volatility": micro.realized_volatility,
            "trade_intensity": micro.trade_intensity,
            
            # Regime (from market_state mapping)
            "regime_volatility": market_state.get("regime_vol", 0.0),
            "regime_trend": market_state.get("regime_trend", 0.0)
        }
        
        return features
