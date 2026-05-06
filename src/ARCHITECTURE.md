# TraderSuit Autonomous Quant Platform

Research-grade, microstructure-aware trading system based on Smart Money Concepts (SMC).

## Core Architecture

The system is designed as a pipeline with strict data contracts:

1.  **Deterministic SMC Layer** (`src/scenarios/`): Generates trade candidates based on market structure and supply/demand zones.
2.  **Market Microstructure Layer** (`src/market_microstructure/`): Computes features from order book snapshots and tick data (spread, OFI, depth imbalance).
3.  **Statistical Feature Fusion** (`src/features/fusion/`): Combines SMC signals with microstructure and regime measurements.
4.  **Meta-Model Filtering** (`src/ml/meta_labeling/`): Scores candidates to estimate the probability of success.
5.  **Risk Gating** (`src/risk/`): Validates approved trades against portfolio constraints and determines position sizing.
6.  **Microstructure-Aware Execution** (`src/execution/`): Optimizes order type (market vs limit) and routes to brokers.
7.  **Event-Driven Backtest** (`src/backtest/`): Simulates the full pipeline under realistic conditions (slippage, spread, fills).

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
