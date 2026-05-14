# Cortex Institutional Quant Platform

Research-grade, regime-aware autonomous trading laboratory.

## Core Architecture

The system is designed as a deterministic-first pipeline with ML-based probability filters:

1.  **Regime & Lifecycle Detection** (`src/regime/`): Classifies market state into Pre-trend, Ignition, Stable Trend, Exhaustion, or Range.
2.  **Deterministic Strategy Family** (`src/strategies/`): specialized logic for Trend Following, Breakout, Pullback, and Mean Reversion.
3.  **Technical Feature Engine** (`src/features/`): Robust, causal technical indicator layer (Hurst, ADX, SMA Slopes).
4.  **Meta-Model Filtering** (`src/ml/meta_labeling/`): Scores trade ideas using secondary feature sets.
5.  **Multi-Asset Risk Engine** (`src/risk/`): Kelly-Criterion sizing scaled by regime stability and asset profile.
6.  **Optimized Execution** (`src/execution/`): Session-aware slippage modeling and RL-optimized entry/exit timing.
7.  **Event-Driven Backtest** (`src/backtest/`): High-fidelity simulation with structured attribution logs.

## Trend Lifecycle & Health System

The platform implements a continuous trend monitoring system that models trends as biological lifecycles:

-   **Lifecycle Stages (0-7)**: From non-trending (0) to ignition (1/2), stable expansion (3/4), overextension (5/6), and reversal risk (7).
-   **Trend Health Engine**: Evaluates slope persistence, retracement quality, and volatility stability.
-   **Late-Trend Protection**: Deterministically blocks new entries when trend maturity or exhaustion risk exceeds defined thresholds.
-   **Persistence Estimation**: Utilizes Hurst Exponent and Kalman filters to differentiate between sustainable trends and noisy rallies.

## Pipeline Flow

`Market Data` → `Regime Classification` → `Strategy Signals` → `Meta-Model (ML Filter)` → `Risk Gating` → `Execution Timing` → `Post-Trade Attribution`

## Key Data Contracts

- `Candle`: Standard OHLCV data.
- `Tick`: Transaction-level data.
- `OrderBookSnapshot`: Depth snapshots.
- `TradeCandidate`: A signal from the SMC engine.
- `ScoredTrade`: A candidate filtered and scored by the meta-model.
- `ExecutionOrder`: A validated order ready for the market.

## Research & Reproducibility

- `src/research/registry/`: Versioned feature definitions.
- `src/research/experiments/`: Config-driven experiments.
- `src/research/tracking/`: Metric logs for Sharpe, MaxDD, and Slippage impact.

## Development Setup

1. Requirements: `python 3.9+`, `numpy`, `scikit-learn`, `pandas`.
2. Run tests: `pytest tests/` (Work in progress).
3. Start research notebook: `jupyter lab`.
