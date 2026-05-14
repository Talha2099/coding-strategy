import unittest
from datetime import datetime, timedelta
from typing import List
from src.core.types.trading import Candle, RegimeState, MTFRegimeState
from src.core.types.strategy import RegimeType, StrategyPhase, StrategyFamily, TradeIdea
from src.strategies.breakout.engine import BreakoutLifecycleEngine
from src.strategies.mean_reversion.engine import MeanReversionLifecycleEngine
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.core.contracts.spec import InstrumentSpec, AssetClass
import numpy as np

class TestScenarioLifecycles(unittest.TestCase):
    def setUp(self):
        self.spec = InstrumentSpec(
            symbol="EURUSD",
            asset_class=AssetClass.FOREX,
            min_lot=0.01,
            lot_step=0.01,
            point_value=100000.0,
            tick_size=0.00001,
            spread_base=0.0001,
            margin_required=0.01
        )
        self.dt = datetime(2023, 1, 1, 12, 0)

    def create_mock_candles(self, n: int, start_price: float, volatility: float = 0.0001) -> List[Candle]:
        candles = []
        price = start_price
        for i in range(n):
            o = price
            h = o + abs(np.random.normal(0, volatility))
            l = o - abs(np.random.normal(0, volatility))
            c = np.random.uniform(l, h)
            candles.append(Candle(ts=self.dt + timedelta(minutes=5*i), open=o, high=h, low=l, close=c, volume=1000))
            price = c
        return candles

    def test_breakout_compression_to_ignition(self):
        engine = BreakoutLifecycleEngine("TestBreakout", self.spec)
        
        # 1. Create compression (flat candles)
        candles = [Candle(self.dt + timedelta(minutes=5*i), 1.1000, 1.1005, 1.0995, 1.1000, 100) for i in range(50)]
        regime = RegimeState(RegimeType.RANGE.value, 0.5, 0.0001, 1.1000)
        
        # Should detect setup
        setup = engine.detect_setup(candles, regime)
        self.assertTrue(setup)
        self.assertEqual(engine.current_phase, StrategyPhase.SETUP_DETECTED)
        
        # 2. Breakout candle
        candles.append(Candle(self.dt + timedelta(minutes=5*50), 1.1000, 1.1050, 1.1000, 1.1045, 5000))
        # Confirm entry
        triggered = engine.confirm_entry(candles)
        self.assertTrue(triggered)
        self.assertEqual(engine.current_phase, StrategyPhase.ENTRY_TRIGGERED)

    def test_breakout_failure_reentry(self):
        engine = BreakoutLifecycleEngine("TestBreakout", self.spec)
        # Mocking an existing idea in position_open
        idea = TradeIdea(
            symbol="EURUSD", asset_class=AssetClass.FOREX, timeframe="M5",
            strategy_name="Test", strategy_family=StrategyFamily.BREAKOUT,
            strategy_subtype="classic", direction="long",
            entry_price=1.1050, stop_loss=1.0990, take_profit=1.1150,
            risk_reward_ratio=2.0, confidence_score=0.8,
            regime_tag=RegimeType.BREAKOUT_ACTIVE,
            lifecycle_phase=StrategyPhase.POSITION_OPEN,
            invalidation_price=1.0990, holding_period_hint="scalp",
            timestamp=self.dt
        )
        
        # Price crashes back mid-range (BB mid is roughly 1.1000 if we started at 1.1000)
        # We need realistic candles for TechnicalFeatureEngine to not crash/give 0
        candles = self.create_mock_candles(100, 1.1000)
        # Force the last candle to be a crash back
        candles[-1] = Candle(self.dt, 1.1050, 1.1050, 1.0990, 1.0995, 1000)
        
        regime = RegimeState(RegimeType.MEAN_REVERTING.value, 0.5, 0.0001)
        updates = engine.on_trade_update(candles, idea, regime)
        
        if updates:
            self.assertTrue(updates.get('exit'))
            self.assertEqual(updates.get('exit_reason'), "false_breakout_reentry")
            self.assertEqual(updates.get('lifecycle_phase'), StrategyPhase.FAILURE)

    def test_mean_reversion_stretched_to_target(self):
        engine = MeanReversionLifecycleEngine("TestMR", self.spec)
        
        # Create stretched setup (Z-score > 2.2)
        candles = self.create_mock_candles(100, 1.1000)
        # Pump it
        for i in range(10):
            last = candles[-1]
            candles.append(Candle(self.dt, last.close, last.close + 0.002, last.close, last.close + 0.002, 1000))
            
        regime = RegimeState(RegimeType.LATE_TREND.value, 0.8, 0.0005)
        
        setup = engine.detect_setup(candles, regime)
        self.assertTrue(setup)
        
        # Confirm on reversal candle (rejection)
        last = candles[-1]
        candles.append(Candle(self.dt, last.close + 0.001, last.close + 0.001, last.close - 0.003, last.close - 0.002, 1000))
        triggered = engine.confirm_entry(candles)
        self.assertTrue(triggered)
        
        # Test full MR target hit in update
        idea = engine.build_trade_idea("EURUSD", candles, regime)
        idea = idea._replace(lifecycle_phase=StrategyPhase.POSITION_OPEN)
        
        # Push price to target (BB Mid)
        from src.features.technical_engine import TechnicalFeatureEngine
        target = TechnicalFeatureEngine.get_candle_features(candles)["bb_mid"][-1]
        
        candles.append(Candle(self.dt, last.close, last.close, target, target, 1000))
        updates = engine.on_trade_update(candles, idea, regime)
        self.assertTrue(updates.get('exit'))
        self.assertEqual(updates.get('exit_reason'), "full_mean_reversion")

    def test_range_fade_to_breakdown(self):
        engine = RangeTradingLifecycleEngine("TestRange", self.spec)
        
        # Create stable range
        candles = [Candle(self.dt + timedelta(minutes=5*i), 1.1000, 1.1010, 1.0990, 1.1002, 100) for i in range(100)]
        regime = RegimeState(RegimeType.RANGE.value, 0.4, 0.0001)
        
        # Near bottom edge
        candles[-1] = Candle(self.dt, 1.0995, 1.0995, 1.0990, 1.0992, 100)
        setup = engine.detect_setup(candles, regime)
        self.assertTrue(setup)
        
        # Trigger fade
        candles.append(Candle(self.dt, 1.0992, 1.0998, 1.0991, 1.0996, 100))
        triggered = engine.confirm_entry(candles)
        self.assertTrue(triggered)
        
        idea = engine.build_trade_idea("EURUSD", candles, regime)
        idea = idea._replace(lifecycle_phase=StrategyPhase.POSITION_OPEN)
        
        # Breakdown occurs (price crashes below BB lower)
        candles.append(Candle(self.dt, 1.0996, 1.0996, 1.0980, 1.0982, 5000))
        updates = engine.on_trade_update(candles, idea, regime)
        self.assertTrue(updates.get('exit'))
        self.assertEqual(updates.get('exit_reason'), "range_breakdown")
        self.assertEqual(updates.get('lifecycle_phase'), StrategyPhase.FAILURE)

if __name__ == "__main__":
    unittest.main()
