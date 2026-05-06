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
  direction: 'long' | 'short';
  entry_zone: number;
  stop_loss: number;
  take_profit: number;
  scenario: string;
  timestamp: Date;
}
