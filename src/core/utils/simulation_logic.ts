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
  { id: 'technical', name: 'Feature Engineering (Hurst/ADX/Volatility)' },
  { id: 'regime', name: 'Regime Classification & Transition' },
  { id: 'router', name: 'Multi-Strategy Signal Routing' },
  { id: 'meta', name: 'ML Meta-Labeling & Prob Calibration' },
  { id: 'risk', name: 'Kelly-Sizing & Asset-Aware Risk' },
  { id: 'exec', name: 'RL-Driven Execution Management' },
  { id: 'attribution', name: 'Attribution & Decay Monitoring' }
];

export class WorkflowSimulator {
  async runStepByStep(
    params: { risk: number; regime: number }, 
    onUpdate: (step: SimulationStep) => void
  ) {
    // 1. Ingest
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'completed', data: { symbol: 'XAUUSD', session: 'Overlap_LN_NY' } });

    // 2. Technical Engine
    onUpdate({ id: 'technical', name: 'Feature Engineering', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'technical', name: 'Feature Engineering', status: 'completed', data: { hurst: 0.62, adx: 32, vol_ratio: 1.4 } });

    // 3. Regime
    onUpdate({ id: 'regime', name: 'Regime Classification', status: 'processing' });
    await new Promise(r => setTimeout(r, 500));
    const regimes = ['TREND', 'RANGE', 'BREAKOUT', 'VOLATILE_UNSTABLE'];
    const idx = Math.floor(params.regime * 3.9);
    const regime = regimes[idx];
    onUpdate({ id: 'regime', name: 'Regime Classification', status: 'completed', data: { state: regime, transition: 'Confirmed' } });

    // 4. Router
    onUpdate({ id: 'router', name: 'Multi-Strategy Signal Routing', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    onUpdate({ id: 'router', name: 'Multi-Strategy Signal Routing', status: 'completed', data: { 
      'Breakout_Family': '1 Signal',
      'Pullback_Family': 'Dormant',
      'Gap_Family': 'N/A' 
    } });

    // 5. Meta
    onUpdate({ id: 'meta', name: 'ML Meta-Labeling', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'meta', name: 'ML Meta-Labeling', status: 'completed', data: { prob_success: '72%', meta_score: 0.68 } });

    // 6. Risk
    onUpdate({ id: 'risk', name: 'Portfolio Risk Management', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    const size = (0.2 * (params.risk / 50)).toFixed(2);
    onUpdate({ id: 'risk', name: 'Portfolio Risk Management', status: 'completed', data: { kelly_fraction: '0.041', trade_size: `${size} lots` } });

    // 7. Exec
    onUpdate({ id: 'exec', name: 'RL-Driven Execution Management', status: 'processing' });
    await new Promise(r => setTimeout(r, 700));
    onUpdate({ id: 'exec', name: 'RL-Driven Execution Management', status: 'completed', data: { fill_quality: 'High', slippage: '2.1 bps' } });

    // 8. Attribution
    onUpdate({ id: 'attribution', name: 'Attribution & Decay Monitoring', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'attribution', name: 'Attribution & Decay Monitoring', status: 'completed', data: { drift: '0.04', roll_sharpe: 2.1 } });
  }
}
