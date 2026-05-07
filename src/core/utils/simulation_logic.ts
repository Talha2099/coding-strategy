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
  { id: 'micro', name: 'Microstructure Feature Extraction' },
  { id: 'regime', name: 'HMM Regime Classification' },
  { id: 'attribution', name: 'Factor Attribution & Decay' },
  { id: 'pattern', name: 'CNN-LSTM Pattern Recognition' },
  { id: 'score', name: 'Meta-Model Probabilistic Scoring' },
  { id: 'risk', name: 'Monte Carlo Risk Gating' },
  { id: 'exec', name: 'SDE-Based Execution Optimization' }
];

export class WorkflowSimulator {
  async runStepByStep(
    params: { risk: number; regime: number }, 
    onUpdate: (step: SimulationStep) => void
  ) {
    // 1. Ingest
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'completed', data: { symbol: 'BTCUSDT', source: 'YahooFinance' } });

    // 2. Micro
    onUpdate({ id: 'micro', name: 'Microstructure Feature Extraction', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'micro', name: 'Microstructure Feature Extraction', status: 'completed', data: { ofi: 0.42, imbalance: -0.12, spread: 0.0001 } });

    // 3. Regime
    onUpdate({ id: 'regime', name: 'HMM Regime Classification', status: 'processing' });
    await new Promise(r => setTimeout(r, 500));
    const regime = params.regime > 0.5 ? 'TRENDING' : 'MEAN_REVERSION';
    onUpdate({ id: 'regime', name: 'HMM Regime Classification', status: 'completed', data: { state: regime, confidence: 0.88 + (params.regime * 0.1) } });

    // 3.1 NEW: Factor Attribution
    onUpdate({ id: 'attribution', name: 'Factor Attribution & Decay', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    onUpdate({ id: 'attribution', name: 'Factor Attribution & Decay', status: 'completed', data: { 
      'OFI_Edge': '0.12 IC (Stable)',
      'Vola_Drift': '-0.02 IC (Degrading)',
      'SMC_Sync': '0.18 IC (Healthy)' 
    } });

    // 4. Pattern
    onUpdate({ id: 'pattern', name: 'CNN-LSTM Pattern Recognition', status: 'processing' });
    await new Promise(r => setTimeout(r, 700));
    onUpdate({ id: 'pattern', name: 'CNN-LSTM Pattern Recognition', status: 'completed', data: { label: 'BULLISH_REVERSAL', score: 0.74 } });

    // 5. Score
    onUpdate({ id: 'score', name: 'Meta-Model Probabilistic Scoring', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'score', name: 'Meta-Model Probabilistic Scoring', status: 'completed', data: { final_prob: 0.68, expected_return: '14.2 bps' } });

    // 6. Risk
    onUpdate({ id: 'risk', name: 'Monte Carlo Risk Gating', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    const kelly = (0.12 * (params.risk / 50)).toFixed(2);
    onUpdate({ id: 'risk', name: 'Monte Carlo Risk Gating', status: 'completed', data: { kelly_fraction: `${kelly}x`, sim_survival: '99.9%' } });

    // 7. Exec
    onUpdate({ id: 'exec', name: 'SDE-Based Execution Optimization', status: 'processing' });
    await new Promise(r => setTimeout(r, 400));
    onUpdate({ id: 'exec', name: 'SDE-Based Execution Optimization', status: 'completed', data: { order_type: 'LIMIT', slippage_est: '0.2 bps' } });
  }
}
