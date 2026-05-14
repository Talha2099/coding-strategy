import unittest
import numpy as np
from datetime import datetime, timedelta
from src.core.types.trading import Candle
from src.features.technical_engine import TechnicalFeatureEngine
from src.regime.engine import RegimeEngine
from src.core.types.strategy import RegimeType

class TestTrendSystem(unittest.TestCase):
    def setUp(self):
        self.regime_engine = RegimeEngine()
        
        # Build synthetic stable trend
        self.candles = []
        start_ts = datetime.utcnow()
        for i in range(200):
            self.candles.append(Candle(
                ts=start_ts + timedelta(minutes=i),
                open=100 + i,
                high=100.5 + i,
                low=99.5 + i,
                close=100.2 + i,
                volume=1000
            ))

    def test_feature_causality(self):
        # Features for 100 candles should match first 100 features of 200 candles
        features_full = TechnicalFeatureEngine.get_candle_features(self.candles)
        features_partial = TechnicalFeatureEngine.get_candle_features(self.candles[:100])
        
        for key in ["sma_20", "rsi", "adx"]:
            if key in features_full and key in features_partial:
                np.testing.assert_array_almost_equal(
                    features_full[key][:100], 
                    features_partial[key],
                    decimal=5,
                    err_msg=f"Causality failure in {key}"
                )

    def test_trend_mid_detection(self):
        state = self.regime_engine.classify(self.candles, "BTCUSD")
        self.assertEqual(state.regime_type, RegimeType.MID_TREND.value)
        self.assertEqual(state.lifecycle_stage, 3)

    def test_trend_late_detection(self):
        # Add climatic move to existing trend
        climatic_candles = list(self.candles)
        last_price = climatic_candles[-1].close
        last_ts = climatic_candles[-1].ts
        for i in range(1, 11):
            climatic_candles.append(Candle(
                ts=last_ts + timedelta(minutes=i),
                open=last_price + (i * 10), # Massive jump
                high=last_price + (i * 10) + 1,
                low=last_price + (i * 10) - 1,
                close=last_price + (i * 10) + 0.5,
                volume=5000 # High volume
            ))
        
        state = self.regime_engine.classify(climatic_candles, "BTCUSD")
        self.assertEqual(state.regime_type, RegimeType.LATE_TREND.value)
        self.assertIn(state.lifecycle_stage, [5, 6])

if __name__ == '__main__':
    unittest.main()
