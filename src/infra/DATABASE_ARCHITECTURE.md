# TraderSuit Backend Infrastructure Architecture

## Overview
A research-grade data, simulation, and validation system designed for the development-first (SQLite) and production-ready (PostgreSQL/TimescaleDB) transition.

## Core Layers

### 1. Data Ingestion & Reconciliation
- **Yahoo Finance (`src/data/ingestion/yahoo_finance.py`)**: Fetches Deep OHLCV history.
- **MT5 Ingestor (`src/data/ingestion/mt5_ingestor.py`)**: Fetches Live quotes, ticks, and recent candles.
- **Reconciler (`src/data/reconciliation/reconciler.py`)**: Merges sources, preferring High-Fidelity MT5 data for recent bars.

### 2. Database Layer (DAL)
- **Engine (`src/infra/database/db_manager.py`)**: SQLite with **WAL Mode** enabled for concurrent read/write and performance.
- **Schema (`src/infra/database/schema.sql`)**: Comprehensive relational schema covering market data, features, regimes, trades, risk, and backtests.
- **Repositories**:
  - `MarketDataRepository`: Instruments, Candles, Ticks.
  - `FeatureRepository`: Feature snapshots and regimes.
  - `TradeRepository`: Candidates, Orders, Fills.
  - `DecisionRepository`: Risk scores, Execution logs, and structured decision tracing.
  - `BacktestRepository`: Backtest summaries and Walk-Forward runs.

### 3. Simulation & Research
- **Backtest Engine (`src/backtest/engine.py`)**: Event-driven simulator support SM C-style execution, realistic slippage, and session-aware spreads.
- **Walk-Forward Engine (`src/backtest/walk_forward.py`)**: Rolling window out-of-sample validator.
- **Live Simulator (`src/execution/live_simulator.py`)**: Shadow-bot mode for real-time paper testing using MT5 live feed.

### 4. Quality & Monitoring
- **Attribution Report (`src/backtest/reporting.py`)**: PnL breakdown by regime, strategy, and market condition.
- **Drift Monitor (`src/features/drift_monitor.py`)**: Detects distribution shifts in features.

## Storage Strategy
- **SQLite**: Local research database with fast prototyping.
- **JSONL**: Parallel file-system storage for deep feature vectors to keep DB size manageable.

## Future Production Migration
- Repositories use abstracted interfaces.
- Schema avoids SQLite-specific dialects where possible.
- SQL queries are centralized in repositories to ease migration to SQLAlchemy or raw PostgreSQL drivers.
