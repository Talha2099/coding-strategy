from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class Experiment:
    id: str
    config_hash: str
    dataset_version: str
    metrics: Dict[str, float]
