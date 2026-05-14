import unittest
import numpy as np
from datetime import datetime, timedelta
from src.core.types.trading import Candle, Tick
from src.core.types.strategy import RegimeType, StrategyFamily
from src.regime.engine import RegimeEngine
from src.strategies.breakout.orb_strategy import ORBStrategy
from src.risk.engine import RiskEngine
from src.core.contracts.spec import InstrumentSpec, AssetClass, SessionType

class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        self.specs = {
            "XAUUSD": InstrumentSpec(
                symbol="XAUUSD",
                asset_class=AssetClass.CFD,
                point_value=100.0,
                contract_size=1,
                min_lot=0.01,
                lot_step=0.01,
                spread_base=0.15
            )
        }
        self.regime_engine = RegimeEngine()
        self.risk_engine = RiskEngine(self.specs)

    def test_regime_classification_trending(self):
        # Create a trending setup
        candles = []
        start_price = 2000.0
        for i in range(100):
            candles.append(Candle(
                symbol="XAUUSD",
                ts=datetime.now() + timedelta(minutes=i),
                open=start_price + i,
                high=start_price + i + 0.5,
                low=start_price + i - 0.5,
                close=start_price + i + 0.1,
                volume=100
            ))
        
        state = self.regime_engine.classify(candles, "XAUUSD")
        # With a clear upward bias and high ADX/Hurst, it should be TREND or BREAKOUT
        self.assertIn(state.regime_type, [RegimeType.TREND.value, RegimeType.BREAKOUT.value])

    def test_risk_sizing_unstable_regime(self):
        # Sizing should be significantly reduced in VOLATILE_UNSTABLE regime
        size_normal = self.risk_engine.position_size(
            "XAUUSD", 0.001, 100000, 10.0, RegimeType.TREND, confidence=0.7
        )
        size_unstable = self.risk_engine.position_size(
            "XAUUSD", 0.01, 100000, 10.0, RegimeType.VOLATILE_UNSTABLE, confidence=0.7
        )
        
        self.assertTrue(size_unstable < size_normal * 0.5)

    def test_orb_strategy_detection(self):
        # Mock ORB setup
        strategy = ORBStrategy()
        # High of first 30 mins
        opening_candles = []
        for i in range(30):
            opening_candles.append(Candle(
                symbol="XAUUSD",
                ts=datetime(2026, 5, 13, 8, 0) + timedelta(minutes=i),
                open=2000, high=2010, low=1990, close=2005, volume=100
            ))
        
        # Next candle breaks high
        trigger_candle = Candle(
            symbol="XAUUSD",
            ts=datetime(2026, 5, 13, 8, 31),
            open=2011, high=2015, low=2011, close=2014, volume=500
        )
        
        ideas = strategy.generate_ideas("XAUUSD", opening_candles + [trigger_candle], RegimeType.BREAKOUT)
        self.assertTrue(len(ideas) > 0)
        self.assertEqual(ideas[0].direction, "long")

if __name__ == '__main__':
    unittest.main()
