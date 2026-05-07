from datetime import datetime
from typing import List, Dict, Optional
from src.core.types.trading import Tick
from src.core.contracts.spec import ContractManager, SessionType

class DataEnricher:
    """
    Enriches raw tick data with session labels, asset classes, and event risk flags.
    """
    def __init__(self, contract_manager: ContractManager):
        self.cm = contract_manager
        
    def enrich_tick(self, tick: Tick) -> Dict:
        spec = self.cm.get_spec(tick.symbol)
        session = self.cm.get_session(tick.ts)
        
        # Check for event risk (e.g. within 30 mins of earnings)
        is_event_imminent = False
        if spec.earnings_dates:
            for edate in spec.earnings_dates:
                diff = abs((edate - tick.ts).total_seconds())
                if diff < 1800: # 30 mins
                    is_event_imminent = True
                    break
                    
        return {
            "ts": tick.ts,
            "symbol": tick.symbol,
            "price": tick.price,
            "size": tick.size,
            "session": session.value,
            "asset_class": spec.asset_class.value,
            "is_event_imminent": is_event_imminent,
            "point_value": spec.point_value,
            "contract_size": spec.contract_size
        }

class DataPipeline:
    def __init__(self, enricher: DataEnricher):
        self.enricher = enricher
        
    def process_stream(self, ticks: List[Tick]) -> List[Dict]:
        return [self.enricher.enrich_tick(t) for t in ticks]
