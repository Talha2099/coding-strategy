import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from src.core.types.trading import Candle, RegimeState
from src.core.utils.logger import system_logger
from src.features.raw_engine import RawFeatureEngine
from src.features.context_engine import ContextFeatureEngine
from src.features.structure_engine import StructureFeatureEngine
from src.features.regime_features import RegimeFeatureEngine
from src.features.lifecycle_features import LifecycleFeatureEngine
from src.features.behavior_engine import BehaviorFeatureEngine
from src.features.validation import FeatureValidationEngine
from src.features.drift_monitor import FeatureDriftMonitor
from src.features.quality_engine import FeatureQualityEngine

from src.features.versioning import FeatureVersioning

from src.features.normalization import FeatureNormalizer
from src.features.storage import FeatureStorage

class FeaturePipeline:
    """
    Unified Feature Pipeline coordinating multiple stages.
    Stages: A (Raw) -> B (Context) -> C (Structure) -> D (Regime) -> E (Lifecycle) -> F (Behavior) -> G (Validation) -> H (Normalization) -> J (Quality) -> K (Storage).
    """
    
    def __init__(self):
        self.validator = FeatureValidationEngine()
        self.quality = FeatureQualityEngine(window=500)
        self.drift_monitor = FeatureDriftMonitor(window=1000)
        self.metadata = FeatureVersioning.get_metadata()
        self.normalizer = FeatureNormalizer()
        self.storage = FeatureStorage()

    def generate_market_state(self, 
                              candles: List[Candle], 
                              regime_state: Optional[RegimeState] = None,
                              symbol: Optional[str] = None) -> Dict[str, np.ndarray]:
        """
        Executes the full multi-stage pipeline.
        Returns a rich dictionary of market state features.
        """
        if not candles: return {}
        
        system_logger.log_event("PIPELINE_EXECUTION", {"version": self.metadata["version"]})
        
        # Stage A: Raw
        raw = RawFeatureEngine.extract(candles)
        
        # Stage B: Context
        context = ContextFeatureEngine.extract(raw, candles, symbol)
        
        # Stage C: Structure
        structure = StructureFeatureEngine.extract(raw)
        
        # Stage D: Regime
        regime = RegimeFeatureEngine.extract(regime_state, len(candles))
        
        # Merge preliminary features for Stage E/F
        temp_features = {**raw, **context, **structure, **regime}
        
        # Stage E: Lifecycle
        lifecycle = LifecycleFeatureEngine.extract(raw, context)
        
        # Merge for Stage F
        all_temp = {**temp_features, **lifecycle}
        
        # Stage F: Behavior
        behavior = BehaviorFeatureEngine.extract(all_temp)
        
        # Stage G: Validation (Internal check)
        final_raw = {**all_temp, **behavior}
        self.validator.validate(final_raw)
        
        # Stage J: Quality Control (Pruning / Importance)
        # Using log_returns as a proxy for target analysis in Stage J
        target_returns = raw.get("log_returns")
        self.quality.analyze_quality(final_raw, target_returns)
        
        # Drift Monitoring (Sampled or full)
        for k in ["trend_quality_score", "mean_reversion_score", "realized_vol"]:
            if k in final_raw:
                self.drift_monitor.record_feature(k, final_raw[k][-1])

        # Stage H: Feature Fusion and Final Normalization (Instrument Aware)
        # Apply instrument-aware adjustments to behavioral scores
        archetype = context.get("instrument_archetype", np.zeros(len(candles)))[-1]
        
        final_features = {}
        for k, v in final_raw.items():
            if "score" in k or "prob" in k:
                final_features[k] = self.normalizer.instrument_adjust(k, v, archetype)
            else:
                final_features[k] = v
        
        return final_features

    def get_latest_state(self, 
                         candles: List[Candle], 
                         regime_state: Optional[RegimeState] = None,
                         symbol: Optional[str] = None,
                         store: bool = False) -> Dict[str, float]:
        """Returns the scalar feature vector for the most recent timestamp."""
        vector = self.generate_market_state(candles, regime_state, symbol)
        scalar_vector = {k: v[-1] if isinstance(v, np.ndarray) else v for k, v in vector.items()}
        
        if store and symbol:
            last_candle = candles[-1]
            ts = last_candle.ts if hasattr(last_candle, 'ts') else str(datetime.utcnow())
            self.storage.store_vector(symbol, str(ts), scalar_vector)
            
        return scalar_vector
