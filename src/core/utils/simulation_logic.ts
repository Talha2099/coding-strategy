export interface SimulationStep {
  id: string;
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  data?: any;
}

export interface FactorInsight {
  name: string;
  ic: number;
  status: 'HEALTHY' | 'DEGRADING' | 'STABLE';
}

export const WORKFLOW_STAGES = [
  { id: 'ingest', name: 'Market Data Ingestion' },
  { id: 'technical', name: 'Technical Engine Feature Extraction' },
  { id: 'regime', name: 'Price Regime Classification' },
  { id: 'router', name: 'Strategy Router Setup Matching' },
  { id: 'backtest', name: 'Simulated Execution Environment' },
  { id: 'analytics', name: 'Performance & Attribution Analytics' },
  { id: 'optimization', name: 'Bayesian Hyperparameter Optimization' },
  { id: 'risk', name: 'Portfolio Risk Management & Sizing' },
  { id: 'exec', name: 'Order Execution Hub' }
];

export class WorkflowSimulator {
  async runStepByStep(
    params: { risk: number; regime: number }, 
    onUpdate: (step: SimulationStep) => void
  ) {
    // 1. Ingest
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'completed', data: { symbol: 'XAUUSD', source: 'HistoricalTick' } });

    // 2. Technical Engine
    onUpdate({ id: 'technical', name: 'Technical Engine Feature Extraction', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'technical', name: 'Technical Engine Feature Extraction', status: 'completed', data: { sma: 2042.1, atr: 5.4, zscore: 1.8 } });

    // 3. Regime
    onUpdate({ id: 'regime', name: 'Price Regime Classification', status: 'processing' });
    await new Promise(r => setTimeout(r, 500));
    const regimes = ['TRENDING_BULL', 'BREAKOUT', 'RANGING', 'TRENDING_BEAR'];
    const idx = Math.floor(params.regime * 3.9);
    const regime = regimes[idx];
    onUpdate({ id: 'regime', name: 'Price Regime Classification', status: 'completed', data: { state: regime, confidence: 0.82 + (params.regime * 0.1) } });

    // 4. Router
    onUpdate({ id: 'router', name: 'Strategy Router Setup Matching', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    onUpdate({ id: 'router', name: 'Strategy Router Setup Matching', status: 'completed', data: { 
      'Breakout_Family': 'Detected',
      'Mean_Rev_Family': 'Dormant',
      'Pullback_Family': 'Preparing' 
    } });

    // 5. Backtest
    onUpdate({ id: 'backtest', name: 'Simulated Execution Environment', status: 'processing' });
    await new Promise(r => setTimeout(r, 700));
    onUpdate({ id: 'backtest', name: 'Simulated Execution Environment', status: 'completed', data: { trades_found: 3, pnl_est: '+12.5 bps' } });

    // 6. Analytics
    onUpdate({ id: 'analytics', name: 'Performance & Attribution Analytics', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'analytics', name: 'Performance & Attribution Analytics', status: 'completed', data: { win_rate: '64.2%', profit_factor: 2.14 } });

    // 7. Optimization
    onUpdate({ id: 'optimization', name: 'Bayesian Hyperparameter Optimization', status: 'processing' });
    await new Promise(r => setTimeout(r, 900));
    onUpdate({ id: 'optimization', name: 'Bayesian Hyperparameter Optimization', status: 'completed', data: { best_window: 24, best_risk: '1.2%', TPE_trials: 50 } });

    // 8. Risk
    onUpdate({ id: 'risk', name: 'Portfolio Risk Management & Sizing', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    const size = (0.2 * (params.risk / 50)).toFixed(2);
    onUpdate({ id: 'risk', name: 'Portfolio Risk Management & Sizing', status: 'completed', data: { pos_size: `${size} lots`, VaR: '1.2%' } });

    // 8. Exec
    onUpdate({ id: 'exec', name: 'Order Execution Hub', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'exec', name: 'Order Execution Hub', status: 'completed', data: { order_type: 'STOP_LIMIT', route: 'LMAX' } });
  }
}
