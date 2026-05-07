export interface SimulationStep {
  id: string;
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  data?: any;
}

export const WORKFLOW_STAGES = [
  { id: 'ingest', name: 'Market Data Ingestion' },
  { id: 'micro', name: 'Microstructure Feature Extraction' },
  { id: 'regime', name: 'HMM Regime Classification' },
  { id: 'pattern', name: 'CNN-LSTM Pattern Recognition' },
  { id: 'score', name: 'Meta-Model Probabilistic Scoring' },
  { id: 'risk', name: 'Monte Carlo Risk Gating' },
  { id: 'exec', name: 'SDE-Based Execution Optimization' }
];

export class WorkflowSimulator {
  async runStepByStep(onUpdate: (step: SimulationStep) => void) {
    // 1. Ingest
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'processing' });
    await new Promise(r => setTimeout(r, 800));
    onUpdate({ id: 'ingest', name: 'Market Data Ingestion', status: 'completed', data: { symbol: 'BTCUSDT', source: 'YahooFinance' } });

    // 2. Micro
    onUpdate({ id: 'micro', name: 'Microstructure Feature Extraction', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'micro', name: 'Microstructure Feature Extraction', status: 'completed', data: { ofi: 0.42, imbalance: -0.12, spread: 0.0001 } });

    // 3. Regime
    onUpdate({ id: 'regime', name: 'HMM Regime Classification', status: 'processing' });
    await new Promise(r => setTimeout(r, 700));
    onUpdate({ id: 'regime', name: 'HMM Regime Classification', status: 'completed', data: { state: 'MEAN_REVERSION', confidence: 0.88 } });

    // 4. Pattern
    onUpdate({ id: 'pattern', name: 'CNN-LSTM Pattern Recognition', status: 'processing' });
    await new Promise(r => setTimeout(r, 1000));
    onUpdate({ id: 'pattern', name: 'CNN-LSTM Pattern Recognition', status: 'completed', data: { label: 'BULLISH_REVERSAL', score: 0.74 } });

    // 5. Score
    onUpdate({ id: 'score', name: 'Meta-Model Probabilistic Scoring', status: 'processing' });
    await new Promise(r => setTimeout(r, 600));
    onUpdate({ id: 'score', name: 'Meta-Model Probabilistic Scoring', status: 'completed', data: { final_prob: 0.68, expected_return: '14.2 bps' } });

    // 6. Risk
    onUpdate({ id: 'risk', name: 'Monte Carlo Risk Gating', status: 'processing' });
    await new Promise(r => setTimeout(r, 900));
    onUpdate({ id: 'risk', name: 'Monte Carlo Risk Gating', status: 'completed', data: { kelly_fraction: '12%', sim_survival: '99.9%' } });

    // 7. Exec
    onUpdate({ id: 'exec', name: 'SDE-Based Execution Optimization', status: 'processing' });
    await new Promise(r => setTimeout(r, 500));
    onUpdate({ id: 'exec', name: 'SDE-Based Execution Optimization', status: 'completed', data: { order_type: 'LIMIT', slippage_est: '0.2 bps' } });
  }
}
