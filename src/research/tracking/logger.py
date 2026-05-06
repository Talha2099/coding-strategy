from typing import Dict
import json
import os
from datetime import datetime

class ExperimentLogger:
    """
    Logs research experiments and backtest results to disk for reproducibility.
    """
    def __init__(self, log_dir: str = "src/research/tracking/logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log_experiment(self, experiment_id: str, config: Dict, metrics: Dict):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "experiment_id": experiment_id,
            "config": config,
            "metrics": metrics
        }
        
        file_path = os.path.join(self.log_dir, f"{experiment_id}.json")
        with open(file_path, "w") as f:
            json.dump(log_entry, f, indent=4)
        
        print(f"Logged experiment {experiment_id} results to {file_path}")
