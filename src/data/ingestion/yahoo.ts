import yahooFinance from 'yahoo-finance2';
import { Candle, Tick } from '../../core/types/trading';

export class YahooIngestor {
  async fetchCandles(symbol: string, start: Date, end: Date, interval: '1m' | '1h' | '1d' = '1h'): Promise<Candle[]> {
    const results = await yahooFinance.chart(symbol, {
      period1: start,
      period2: end,
      interval: interval === '1m' ? '1m' : interval === '1h' ? '60m' : '1d'
    }) as any;

    return (results.quotes || []).map((q: any) => ({
      ts: new Date(q.date),
      open: q.open || 0,
      high: q.high || 0,
      low: q.low || 0,
      close: q.close || 0,
      volume: q.volume || 0
    }));
  }

  /**
   * Generates synthetic ticks from OHLC data to simulate microstructure
   * when live tick data is unavailable.
   */
  generateSyntheticTicks(candle: Candle): Tick[] {
    const ticks: Tick[] = [];
    const mid = (candle.open + candle.high + candle.low + candle.close) / 4;
    
    // Simple 4-tick approximation of OHLC path
    const prices = [candle.open, candle.high, candle.low, candle.close];
    prices.forEach((p, i) => {
      ticks.push({
        ts: candle.ts,
        price: p,
        size: candle.volume / 4,
        side: i % 2 === 0 ? 'buy' : 'sell'
      });
    });
    
    return ticks;
  }
}
