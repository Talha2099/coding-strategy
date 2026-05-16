import unittest
import uuid
import json
from src.infra.database.db_manager import db_manager
from src.infra.database.repositories.trade_repo import TradeRepository
from src.infra.database.repositories.decision_repo import DecisionRepository
from src.infra.database.repositories.backtest_repo import BacktestRepository

class TestBacktestInfrastructure(unittest.TestCase):
    
    def test_decision_logging(self):
        cand_id = str(uuid.uuid4())
        
        # Log Setup Event
        DecisionRepository.log_event(
            event_type="SETUP",
            ref_id=cand_id,
            market_snapshot={"price": 100},
            decision={"signal": "LONG"}
        )
        
        # Log Risk Decision
        DecisionRepository.log_risk_decision({
            "candidate_id": cand_id,
            "risk_score": 0.8,
            "position_size": 10.0,
            "is_approved": True
        })
        
        logs = DecisionRepository.get_logs_for_candidate(cand_id)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['event_type'], 'SETUP')

    def test_backtest_persistence(self):
        bt_id = str(uuid.uuid4())
        backtest_data = {
            "backtest_id": bt_id,
            "name": "Trend Alpha",
            "initial_capital": 100000.0,
            "final_equity": 105000.0,
            "total_trades": 50,
            "sharpe_ratio": 1.2
        }
        BacktestRepository.save_backtest_run(backtest_data)
        
        summary = BacktestRepository.get_backtest_summary(bt_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary['sharpe_ratio'], 1.2)

if __name__ == '__main__':
    unittest.main()
