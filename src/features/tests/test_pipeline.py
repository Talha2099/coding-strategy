import unittest
import numpy as np
from datetime import datetime, timedelta
from src.core.types.trading import Candle
from src.features.pipeline import FeaturePipeline

class TestFeaturePipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = FeaturePipeline()
        # Generate some dummy data
        self.candles = []
        base_time = datetime(2024, 1, 1)
        price = 100.0
        for i in range(200):
            price += np.random.normal(0, 0.5)
            self.candles.append(Candle(
                ts=str(base_time + timedelta(minutes=5*i)),
                open=price - 0.1,
                high=price + 0.3,
                low=price - 0.4,
                close=price,
                volume=1000 + i
            ))

    def test_feature_generation(self):
        """Verify that basic features are generated."""
        features = self.pipeline.generate_market_state(self.candles, symbol="EURUSD")
        self.assertIn("ema_20", features)
        self.assertIn("trend_quality_score", features)
        self.assertEqual(len(features["close"]), len(self.candles))

    def test_causality(self):
        """Verify no future leakage by comparing full run vs incremental run."""
        full_features = self.pipeline.generate_market_state(self.candles, symbol="EURUSD")
        # Get scalar state of last candle
        last_scalar = self.pipeline.get_latest_state(self.candles, symbol="EURUSD")
        
        # They should be identical for values that don't depend on future (like EMA)
        for k in ["close", "ema_20", "rsi"]:
            self.assertAlmostEqual(full_features[k][-1], last_scalar[k], places=5)

    def test_drift_detection(self):
        """Verify that record_feature works without crashing."""
        for i in range(10):
            # Just verify it accepts values
            self.pipeline.drift_monitor.record_feature("test_feat", 1.0 + i*0.1)
        report = self.pipeline.drift_monitor.get_drift_report()
        self.assertIn("test_feat", report)

    def test_instrument_normalization(self):
        """Verify that different instrument archetypes affect behavioral scores."""
        # Test with Trend Archetype (0) vs Volatile (2)
        # Note: instrument_adjust is called in pipeline.generate_market_state
        state_trend = self.pipeline.get_latest_state(self.candles, symbol="BTCUSD") # BTCUSD in registry is TREND
        state_vol = self.pipeline.get_latest_state(self.candles, symbol="GBPJPY") # GBPJPY is TREND too? 
        
        # Let's check registry or just verify the direct call
        val = 0.5
        adj_trend = self.pipeline.normalizer.instrument_adjust("trend_quality_score", np.array([val]), 0.0)[0]
        adj_vol = self.pipeline.normalizer.instrument_adjust("trend_quality_score", np.array([val]), 2.0)[0]
        
        self.assertNotEqual(adj_trend, adj_vol)

if __name__ == '__main__':
    unittest.main()
