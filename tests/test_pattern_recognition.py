import pytest
import numpy as np
from datetime import datetime
from src.ml.pattern_recognition.model import PatternRecognizer
from src.core.types.trading import TradeCandidate

def test_pattern_recognition_bullish():
    recognizer = PatternRecognizer()
    candidate = TradeCandidate("c1", "BTC", "long", 100, 90, 110, "test", datetime.now())
    
    # Sharp reversal shape: [High, Mid, Low, Mid, High]
    price_window = [110, 108, 105, 102, 100, 98, 95, 98, 102, 105]
    
    result = recognizer.calculate_score(candidate, price_window, {"entry": 100})
    
    assert result["probability"] > 0.5
    assert "BULLISH" in result["label"]

def test_pattern_recognition_ranging():
    recognizer = PatternRecognizer()
    candidate = TradeCandidate("c2", "BTC", "long", 100, 90, 110, "test", datetime.now())
    
    # Ranging prices around 100: [100.1, 99.9, 100.0, 100.2, 99.8, ...]
    price_window = [110, 105, 102, 100.1, 99.9, 100.0, 100.1, 99.8, 100.2, 100.0, 99.9, 100.1, 99.8, 100.2, 100.0]
    
    result = recognizer.calculate_score(candidate, price_window, {"entry": 100})
    
    assert result["features"]["is_ranging"] is True
    assert "ACCUMULATION" in result["label"] or "CONSOLIDATION" in result["label"]
    assert result["features"]["level_touches"] > 2
