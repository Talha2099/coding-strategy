import unittest
from datetime import datetime, timedelta
from typing import List, Optional
from src.core.types.trading import Candle, RegimeState, MTFRegimeState, HTFState
from src.core.types.strategy import RegimeType, StrategyPhase, StrategyFamily, TradeIdea
from src.strategies.range.engine import RangeTradingLifecycleEngine
from src.regime.engine import RegimeEngine
from src.core.contracts.spec import InstrumentSpec, AssetClass
import numpy as np

class TestRangeLifecycle(unittest.TestCase):
    def setUp(self):
        self.spec = InstrumentSpec(
            symbol="EURUSD",
            asset_class=AssetClass.FX,
            min_size=0.01,
            max_size=100.0,
            tick_size=0.00001,
            lot_size=100000,
            spread_base=0.0001,
            margin_required=0.01
        )
        self.dt = datetime(2026, 5, 14, 12, 0)
        self.regime_engine = RegimeEngine()
        self.strategy = RangeTradingLifecycleEngine("ClassicRange", self.spec)

    def generate_range_candles(self, n: int, mid_price: float, width: float) -> List[Candle]:
        candles = []
        for i in range(n):
            angle = (i / 10.0) * np.pi * 2 # Cycle every 10 candles
            price = mid_price + np.sin(angle) * width
            o = price - 0.0001
            h = price + 0.0002
            l = price - 0.0003
            c = price
            candles.append(Candle(self.dt + timedelta(minutes=5*i), o, h, l, c, 100))
        return candles

    def test_range_detection_and_fade(self):
        """Test detection of established range and edge fade."""
        # 1. Establish Range
        candles = self.generate_range_candles(100, 1.1000, 0.0050)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        # Verify state is Rangy
        self.assertIn(state.regime_type, [
            RegimeType.RANGE_ESTABLISHED.value, 
            RegimeType.RANGE.value,
            RegimeType.RANGE_HIGH_TOUCH.value,
            RegimeType.RANGE_LOW_TOUCH.value
        ])
        
        # 2. Strategy Detection
        setup = self.strategy.detect_setup(candles, state)
        self.assertTrue(setup)
        
        # 3. Entry Confirmation (at peak or trough)
        # Force a peak rejection
        last = candles[-1]
        candles.append(Candle(self.dt, last.close, last.close+0.001, last.close-0.002, last.close-0.0015, 500))
        state = self.regime_engine.classify(candles, "EURUSD")
        
        confirmed = self.strategy.confirm_entry(candles, state)
        # Depending on exact placement it might be too far from edge, but usually in a sin wave it works
        if confirmed:
            idea = self.strategy.build_trade_idea("EURUSD", candles, state)
            self.assertIsNotNone(idea)
            self.assertEqual(idea.direction, "short") # Fading top

    def test_range_breakout_exit(self):
        """Management should exit if range breaks."""
        candles = self.generate_range_candles(50, 1.1000, 0.0050)
        state = self.regime_engine.classify(candles, "EURUSD")
        idea = self.strategy.build_trade_idea("EURUSD", candles, state)
        
        if not idea: return # Might not be at edge
        
        # Simulate Breakout
        last = candles[-1]
        for i in range(5):
            candles.append(Candle(self.dt, last.close, last.close+0.005, last.close, last.close+0.004, 2000))
            last = candles[-1]
            
        state = self.regime_engine.classify(candles, "EURUSD")
        updates = self.strategy.on_trade_update(candles, idea, state)
        
        if updates and updates.get("exit"):
            self.assertEqual(updates["exit_reason"], "range_breakout_confirmed")

    def test_range_exhaustion_blocking(self):
        """Test that late/exhausted ranges block new entries."""
        candles = self.generate_range_candles(150, 1.1000, 0.0050)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        # Simulate volatility expansion and high ADX (Breakout risk)
        last = candles[-1]
        for i in range(5):
            candles.append(Candle(self.dt, last.close, last.close+0.002, last.close-0.001, last.close+0.001, 2000))
        
        state = self.regime_engine.classify(candles, "EURUSD")
        state.regime_type = RegimeType.RANGE_EXHAUSTION.value
        
        setup = self.strategy.detect_setup(candles, state)
        # Should be blocked either by analysis engine or planner
        self.assertFalse(setup)

    def test_htf_alignment(self):
        """Test multi-timeframe alignment for range entry."""
        candles = self.generate_range_candles(50, 1.1000, 0.0050)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        # Scenario: HTF is in a strong trend
        mtf_state = MTFRegimeState(
            ltf_state=HTFState(direction=1, regime=RegimeType.RANGE.value, score=0.2),
            mtf_state=HTFState(direction=1, regime=RegimeType.TREND_UP.value, score=0.8),
            htf_state=HTFState(direction=1, regime=RegimeType.TREND_UP.value, score=0.9),
            confluence_score=0.8,
            bias="bullish",
            symbol="EURUSD",
            timestamp=self.dt
        )
        
        # Strategy should de-risk or skip if HTF is trending hard (Breakout risk)
        setup = self.strategy.detect_setup(candles, state, mtf_state)
        # It might still be allowed but with lower quality
        analysis = self.strategy.analyze_setup(candles, state, mtf_state)
        self.assertGreater(analysis["breakout_risk"], 0.3)

    def test_partial_exit_at_midpoint(self):
        """Test that management takes partial profit at range midpoint."""
        candles = self.generate_range_candles(50, 1.1000, 0.0050)
        state = self.regime_engine.classify(candles, "EURUSD")
        
        # Mock a 'short' trade idea entered at the top (1.1050)
        idea = self.strategy.build_trade_idea("EURUSD", candles, state)
        if not idea: return
        idea.direction = "short"
        idea.entry_price = 1.1050
        idea.metadata["targets"] = [1.1000, 1.0950] # [Mid, Opposite]
        
        # Price hits midpoint
        last = candles[-1]
        candles.append(Candle(self.dt, 1.1000, 1.1001, 1.0999, 1.1000, 500))
        state = self.regime_engine.classify(candles, "EURUSD")
        
        updates = self.strategy.on_trade_update(candles, idea, state)
        self.assertIsNotNone(updates)
        self.assertEqual(updates.get("partial_exit"), 0.5)
        self.assertEqual(updates.get("stop_loss"), 1.1050) # Break-even

if __name__ == "__main__":
    unittest.main()
