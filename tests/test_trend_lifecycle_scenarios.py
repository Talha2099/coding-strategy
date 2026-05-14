import unittest
from datetime import datetime, timedelta
from typing import List, Optional
from src.core.types.trading import Candle, RegimeState, MTFRegimeState, HTFState
from src.core.types.strategy import RegimeType, StrategyPhase, StrategyFamily, TradeIdea
from src.strategies.trend.lifecycle_trend import LifecycleTrendStrategy
from src.regime.engine import RegimeEngine
from src.risk.asset_aware_risk import MultiAssetRiskEngine
from src.core.contracts.spec import InstrumentSpec, AssetClass
import numpy as np

class TestTrendLifecycleScenarios(unittest.TestCase):
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
        self.dt = datetime(2026, 5, 14, 12, 0)
        self.regime_engine = RegimeEngine()
        self.strategy = LifecycleTrendStrategy(self.spec)
        self.risk_engine = MultiAssetRiskEngine({"EURUSD": self.spec}, risk_per_trade=0.01)

    def generate_trend_candles(self, n: int, start_price: float, slope: float, vol: float = 0.0001) -> List[Candle]:
        candles = []
        price = start_price
        for i in range(n):
            o = price
            price += slope + np.random.normal(0, vol)
            h = max(o, price) + abs(np.random.normal(0, vol))
            l = min(o, price) - abs(np.random.normal(0, vol))
            c = price
            candles.append(Candle(ts=self.dt + timedelta(minutes=5*i), open=o, high=h, low=l, close=c, volume=1000))
        return candles

    def test_full_lifecycle_progression(self):
        """Compression -> Breakout -> Early -> Mid -> Pullback -> Continuation -> Late -> Exhaustion"""
        # 1. Pre-trend Compression
        candles = [Candle(self.dt + timedelta(minutes=5*i), 1.1000, 1.1002, 1.0998, 1.1000, 100) for i in range(50)]
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertEqual(state.regime_type, RegimeType.PRE_TREND_COMPRESSION.value)
        
        # 2. Early Trend (Ignition)
        candles += self.generate_trend_candles(10, 1.1000, 0.0005)
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertEqual(state.regime_type, RegimeType.EARLY_TREND.value)
        self.assertTrue(self.strategy.detect_setup(candles, state))
        
        # 3. Confirmed / Mid Trend
        candles += self.generate_trend_candles(20, candles[-1].close, 0.0005)
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertIn(state.regime_type, [RegimeType.CONFIRMED_TREND.value, RegimeType.MID_TREND.value])
        
        # 4. Pullback
        last_price = candles[-1].close
        for i in range(8):
            o = last_price
            last_price -= 0.0003
            candles.append(Candle(self.dt + timedelta(minutes=5*(len(candles)+i)), o, o+0.0001, last_price-0.0001, last_price, 500))
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertEqual(state.regime_type, RegimeType.PULLBACK_IN_TREND.value)
        
        # 5. Continuation Ready
        last = candles[-1]
        candles.append(Candle(self.dt + timedelta(minutes=5*(len(candles)+1)), last.close, last.close+0.002, last.close, last.close+0.0015, 2000))
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertEqual(state.regime_type, RegimeType.CONTINUATION_READY.value)
        
        # 6. Late Trend / Overextension
        candles += self.generate_trend_candles(50, candles[-1].close, 0.001)
        state = self.regime_engine.classify(candles, "EURUSD")
        self.assertIn(state.regime_type, [RegimeType.LATE_TREND.value, RegimeType.EXHAUSTION_RISK.value])
        
        # 7. Exhaustion & Exit Decision
        idea = self.strategy.build_trade_idea("EURUSD", candles, state)
        # If we already have a position, management should tighten
        if idea:
            updates = self.strategy.on_trade_update(candles, idea, state)
            if state.exhaustion_risk > 0.85:
                self.assertTrue(updates.get("exit") or "stop_loss" in updates)

    def test_mtf_trend_alignment(self):
        """HTF Trend with LTF Pullback entry."""
        candles = self.generate_trend_candles(50, 1.1000, 0.0002)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        # Mock MTF State: HTF is bullish
        mtf_state = MTFRegimeState(
            ltf_state=HTFState(direction=1, regime=RegimeType.EARLY_TREND.value, score=0.8),
            mtf_state=HTFState(direction=1, regime=RegimeType.CONFIRMED_TREND.value, score=0.8),
            htf_state=HTFState(direction=1, regime=RegimeType.MID_TREND.value, score=0.9),
            confluence_score=0.9,
            bias="bullish"
        )
        
        # Should detect setup when LTF has a pullback but HTF is strong
        state.regime_type = RegimeType.PULLBACK_IN_TREND.value
        setup = self.strategy.detect_setup(candles, state, mtf_state)
        self.assertTrue(setup)

    def test_risk_scaling_by_stage(self):
        """Test that early trend gets larger size than late trend."""
        # Early Stage
        early_state = RegimeState("EURUSD", RegimeType.EARLY_TREND.value, 0.001, 1.0, 0.8, 0.2, 0.1, 1, 0.6)
        early_size = self.risk_engine.get_position_sizing("EURUSD", 0.001, 100000, 0.005, early_state)
        
        # Late Stage
        late_state = RegimeState("EURUSD", RegimeType.LATE_TREND.value, 0.001, 1.0, 0.4, 0.8, 2.8, 5, 0.4)
        late_size = self.risk_engine.get_position_sizing("EURUSD", 0.001, 100000, 0.005, late_state)
        
        self.assertGreater(early_size, late_size)

    def test_management_trailing_stop(self):
        """Test that management trails stop during healthy trend."""
        candles = self.generate_trend_candles(50, 1.1000, 0.0005)
        state = self.regime_engine.classify(candles, "EURUSD")
        idea = self.strategy.build_trade_idea("EURUSD", candles, state)
        
        # Progress trend
        candles += self.generate_trend_candles(10, candles[-1].close, 0.0005)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        updates = self.strategy.on_trade_update(candles, idea, state)
        self.assertIsNotNone(updates)
        if "stop_loss" in updates:
            self.assertGreater(updates["stop_loss"], idea.stop_loss)

    def test_exhaustion_exit(self):
        """Management should exit on climax/exhaustion."""
        candles = self.generate_trend_candles(100, 1.1000, 0.001)
        state = self.regime_engine.classify(candles, "EURUSD")
        idea = self.strategy.build_trade_idea("EURUSD", candles, state)
        
        # Climax/Spike
        last = candles[-1]
        candles.append(Candle(self.dt, last.close, last.close+0.02, last.close, last.close+0.018, 5000))
        state = self.regime_engine.classify(candles, "EURUSD")
        state.exhaustion_risk = 0.95
        state.health_score = 0.3
        
        updates = self.strategy.on_trade_update(candles, idea, state)
        self.assertTrue(updates.get("exit"))
        self.assertIn("exhaustion", updates.get("exit_reason", "").lower())

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
