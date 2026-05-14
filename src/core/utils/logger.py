import json
import logging
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """
    Emits machine-readable JSON logs for system events.
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Ensure we don't add multiple handlers if initialized multiple times
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        log_entry = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.logger.info(json.dumps(log_entry))

# Global logger for the system
system_logger = StructuredLogger("CortexSystem")
