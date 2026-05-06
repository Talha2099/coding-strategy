# TraderSuit Autonomous Quant Platform

Research-grade, microstructure-aware trading system based on Smart Money Concepts (SMC).

## Features

- **Deterministic Alpha**: Rule-based SMC signal generation (Liquidity sweeps, BOS, CHoCH).
- **Microstructure Intelligence**: Order-flow imbalance (OFI), Depth imbalance, and dynamic slippage modeling.
- **Meta-Labeling**: ML filtering layer to reduce false positives from the base strategy.
- **Event-Driven Backtester**: Realistic fill simulation with spread and commission impact.
- **Research Registry**: Versioned feature and experiment tracking for reproducible quant workflows.

## Pipeline Architecture

`Scenarios (SMC)` → `Feature Fusion` → `Meta-Model (ML Filter)` → `Risk Gating` → `Execution Decision` → `OMS/Broker`

## Directory Structure

- `src/core/`: Event system, clock, and fundamental types.
- `src/data/`: Data contracts and ingestion pipelines.
- `src/market_microstructure/`: Orderbook and trade analytics.
- `src/ml/`: Meta-model training and inference.
- `src/research/`: Experiment tracking and reporting.

## Setup

```bash
# Install dependencies
npm install
# Note: Platform logic is implemented in Python-ready structures, 
# though the dashboard is a Next.js React client.
```

## Dashboard

The dashboard provides a real-time view into the engine's state, active zones, and backtest results. Use the "Run Backtest" button to trigger a simulated research run.
