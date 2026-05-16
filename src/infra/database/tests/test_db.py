import unittest
import os
import sqlite3
from src.infra.database.db_manager import DatabaseManager
from src.infra.database.repositories.market_data_repo import MarketDataRepository

class TestDatabaseInfrastructure(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_trader_suit.db"
        # Force re-init for test
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = DatabaseManager(db_path=self.db_path)

    def test_wal_mode_enabled(self):
        conn = sqlite3.connect(self.db_path)
        res = conn.execute("PRAGMA journal_mode;").fetchone()
        self.assertEqual(res[0].lower(), "wal")
        conn.close()

    def test_market_data_persistence(self):
        # 1. Save Instrument
        instr = {
            "symbol": "EURUSD",
            "name": "Euro Dollar",
            "asset_class": "FOREX",
            "archetype": "TREND"
        }
        MarketDataRepository.save_instrument(instr)
        
        # 2. Save Candles
        candles = [
            {"timestamp": "2024-01-01T00:00:00", "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15, "volume": 1000},
            {"timestamp": "2024-01-01T00:05:00", "open": 1.15, "high": 1.25, "low": 1.1, "close": 1.2, "volume": 1200}
        ]
        MarketDataRepository.save_candles("EURUSD", "M5", "YAHOO", candles)
        
        # 3. Retrieve
        saved = MarketDataRepository.get_candles("EURUSD", "M5")
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]['close'], 1.15)

    def tearDown(self):
        if os.path.exists(self.db_path):
            # Clean up all WAL files too
            for ext in ['', '-wal', '-shm']:
                if os.path.exists(self.db_path + ext):
                    try: os.remove(self.db_path + ext)
                    except: pass

if __name__ == '__main__':
    unittest.main()
