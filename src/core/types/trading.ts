export interface Candle {
  ts: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Tick {
  ts: Date;
  price: number;
  size: number;
  side: 'buy' | 'sell';
}

export interface TradeCandidate {
  id: string;
  symbol: string;
  asset_class: string;
  direction: 'long' | 'short';
  entry_zone_id: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  strategy_family: string;
  strategy_name: string;
  regime_at_entry: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface StrategySignal {
  symbol: string;
  direction: 'long' | 'short';
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  features: Record<string, number>;
  strategy_name: string;
  timestamp: Date;
}

export interface RiskDecision {
  signal_id: string;
  approved: boolean;
  size: number;
  reason: string;
  max_drawdown_impact: number;
  timestamp: Date;
}

export interface Action {
  type: 'enter' | 'exit' | 'scale_in' | 'scale_out' | 'update_stop' | 'cancel';
  symbol: string;
  side: 'buy' | 'sell';
  size: number;
  price?: number;
  order_type: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface RegimeState {
  symbol: string;
  regime_type: string;
  probabilities: Record<string, number>;
  volatility: number;
  trend_strength: number;
  timestamp: Date;
}

export interface ExecutionReport {
  action_id: string;
  order_id: string;
  status: 'filled' | 'rejected' | 'canceled' | 'partial';
  fill_price?: number;
  fill_size: number;
  slippage: number;
  commission: number;
  venue: string;
  timestamp: Date;
}

export interface TradeLogEvent {
  event_id: string;
  trade_id: string;
  event_type: string;
  message: string;
  data: Record<string, any>;
  timestamp: Date;
}
