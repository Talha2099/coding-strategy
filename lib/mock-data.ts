import { subDays, subHours, format } from 'date-fns';

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Zone {
  id: string;
  type: 'order_block' | 'fvg' | 'sr';
  direction: 1 | -1;
  upperBound: number;
  lowerBound: number;
  state: 'fresh' | 'tapped' | 'mitigated' | 'broken';
  strength: number;
  timeframe: string;
}

export interface TradeCandidate {
  id: string;
  symbol: string;
  side: 1 | -1;
  strategyName: string;
  strategyFamily: string;
  regime: string;
  entryTime: string;
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  score: number;
  probability: number;
  status: 'pending' | 'executed' | 'closed' | 'rejected';
}

export const MOCK_PERFORMANCE = Array.from({ length: 50 }, (_, i) => ({
  time: format(subHours(new Date(), 50 - i), 'HH:mm'),
  equity: 10000 + Math.sin(i * 0.2) * 500 + i * 50,
  drawdown: Math.abs(Math.cos(i * 0.3) * 200),
}));

export const MOCK_ZONES: Zone[] = [
  {
    id: 'z1',
    type: 'order_block',
    direction: 1,
    upperBound: 65200,
    lowerBound: 65000,
    state: 'fresh',
    strength: 0.92,
    timeframe: 'H1',
  },
  {
    id: 'z2',
    type: 'fvg',
    direction: -1,
    upperBound: 68500,
    lowerBound: 68200,
    state: 'tapped',
    strength: 0.75,
    timeframe: 'H4',
  },
  {
    id: 'z3',
    type: 'order_block',
    direction: 1,
    upperBound: 62100,
    lowerBound: 61850,
    state: 'mitigated',
    strength: 0.88,
    timeframe: 'D1',
  },
];

export const MOCK_TRADES: TradeCandidate[] = [
  {
    id: 't1',
    symbol: 'XAUUSD',
    side: 1,
    strategyName: 'DonchianBreakout',
    strategyFamily: 'Breakout',
    regime: 'BREAKOUT',
    entryTime: subHours(new Date(), 2).toISOString(),
    entryPrice: 2045.50,
    stopLoss: 2038.20,
    takeProfit: 2060.00,
    score: 8.5,
    probability: 0.82,
    status: 'executed',
  },
  {
    id: 't2',
    symbol: 'GBPUSD',
    side: -1,
    strategyName: 'BollingerMR',
    strategyFamily: 'Mean Reversion',
    regime: 'RANGING',
    entryTime: subHours(new Date(), 5).toISOString(),
    entryPrice: 1.2650,
    stopLoss: 1.2685,
    takeProfit: 1.2580,
    score: 7.2,
    probability: 0.68,
    status: 'closed',
  },
  {
    id: 't3',
    symbol: 'BTCUSDT',
    side: 1,
    strategyName: 'VWAPPullback',
    strategyFamily: 'Pullback',
    regime: 'TRENDING BULL',
    entryTime: subHours(new Date(), 1).toISOString(),
    entryPrice: 65150,
    stopLoss: 64800,
    takeProfit: 67000,
    score: 9.1,
    probability: 0.79,
    status: 'pending',
  },
];
