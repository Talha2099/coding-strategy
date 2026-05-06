from typing import List, Optional
from src.core.types.trading import OrderBookSnapshot, Tick, MicrostructureFeatures
import numpy as np

class MicrostructureEngine:
    def __init__(self):
        self.current_snapshot: Optional[OrderBookSnapshot] = None
        self.trades: List[Tick] = []
        self.last_compute_ts = None

    def update_orderbook(self, snapshot: OrderBookSnapshot) -> None:
        self.current_snapshot = snapshot

    def update_trades(self, tick: Tick) -> None:
        self.trades.append(tick)
        # Keep buffer manageable
        if len(self.trades) > 1000:
            self.trades.pop(0)

    def compute_features(self, skip_ofi: bool = False) -> MicrostructureFeatures:
        if not self.current_snapshot:
            # Handle case where only trades are available (OFI-only or partial)
            mid_price = self.trades[-1].price if self.trades else 0
            return MicrostructureFeatures(0, mid_price, 0, 0, 0, 0)
        
        best_bid = self.current_snapshot.bids[0][0] if self.current_snapshot.bids else 0
        best_ask = self.current_snapshot.asks[0][0] if self.current_snapshot.asks else 0
        
        spread = best_ask - best_bid
        mid_price = (best_ask + best_bid) / 2
        
        # Depth Imbalance
        bid_depth = sum(s for p, s in self.current_snapshot.bids)
        ask_depth = sum(s for p, s in self.current_snapshot.asks)
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0
        
        # Order Flow Imbalance (from recent trades)
        ofi = 0
        if not skip_ofi:
            buy_vol = sum(t.size for t in self.trades if t.side == "buy")
            sell_vol = sum(t.size for t in self.trades if t.side == "sell")
            ofi = (buy_vol - sell_vol) / (buy_vol + sell_vol) if (buy_vol + sell_vol) > 0 else 0
        
        # Realized Volatility (approx from trades)
        if len(self.trades) > 1:
            prices = [t.price for t in self.trades]
            returns = np.diff(np.log(prices))
            realized_vol = np.std(returns)
        else:
            realized_vol = 0
            
        trade_intensity = len(self.trades) # Simple count for now
        
        return MicrostructureFeatures(
            spread=spread,
            mid_price=mid_price,
            imbalance=imbalance,
            order_flow_imbalance=ofi,
            realized_volatility=float(realized_vol),
            trade_intensity=float(trade_intensity)
        )
