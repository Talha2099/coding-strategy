-- TraderSuit Core Schema (SQLite)
-- Version: 1.0.0

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
-- 1. CORE MARKET DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS instruments (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    asset_class TEXT, -- EQUITY, FOREX, CRYPTO, COMMODITY, INDEX
    archetype TEXT,   -- TREND, RANGE, VOLATILE, MEAN_REVERTING
    point_value REAL DEFAULT 1.0,
    tick_size REAL DEFAULT 0.01,
    contract_size REAL DEFAULT 1.0,
    currency TEXT DEFAULT 'USD',
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL, -- M1, M5, M15, H1, D1
    timestamp DATETIME NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    source TEXT NOT NULL, -- YAHOO, MT5, BINANCE
    is_final INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol),
    UNIQUE(symbol, timeframe, timestamp, source)
);

CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    bid REAL,
    ask REAL,
    last REAL,
    volume REAL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol)
);

-- ============================================================
-- 2. FEATURE AND REGIME TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS feature_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    version TEXT NOT NULL, -- Code version / Feature set version
    features_json TEXT NOT NULL, -- Store as JSON for flexibility
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol)
);

CREATE TABLE IF NOT EXISTS regime_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    current_regime TEXT NOT NULL, -- BULL_TREND, BEAR_TREND, HIGH_VOL_RANGE, etc.
    regime_score REAL,
    probabilities_json TEXT, -- probabilities of each regime
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol)
);

-- ============================================================
-- 3. STRATEGY AND SIGNAL TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS trade_candidates (
    id TEXT PRIMARY KEY, -- UUID
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    strategy_name TEXT NOT NULL,
    direction INTEGER NOT NULL, -- 1 for Long, -1 for Short
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    risk_reward_ratio REAL,
    validation_score REAL,
    raw_signal_json TEXT,
    regime_at_time TEXT,
    status TEXT DEFAULT 'PENDING', -- PENDING, VALIDATED, REJECTED, EXECUTED
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol)
);

CREATE TABLE IF NOT EXISTS rejected_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    rejection_code TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES trade_candidates(id)
);

-- ============================================================
-- 4. RISK AND EXECUTION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    symbol TEXT NOT NULL,
    order_type TEXT NOT NULL, -- MARKET, LIMIT, STOP
    direction INTEGER NOT NULL,
    quantity REAL NOT NULL,
    price REAL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT DEFAULT 'OPEN', -- OPEN, FILLED, CANCELLED, REJECTED
    broker_order_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(symbol) REFERENCES instruments(symbol)
);

CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    fill_price REAL NOT NULL,
    quantity REAL NOT NULL,
    commission REAL DEFAULT 0,
    slippage REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);

-- ============================================================
-- 5. BACKTEST / WALK-FORWARD TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS backtests (
    backtest_id TEXT PRIMARY KEY,
    name TEXT,
    strategy_config_json TEXT,
    start_date DATETIME,
    end_date DATETIME,
    initial_capital REAL,
    final_equity REAL,
    total_trades INTEGER,
    sharpe_ratio REAL,
    max_drawdown REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS walk_forward_runs (
    run_id TEXT PRIMARY KEY,
    backtest_id TEXT,
    symbol TEXT,
    config_json TEXT,
    start_date DATETIME,
    end_date DATETIME,
    oos_sharpe REAL,
    oos_pnl REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(backtest_id) REFERENCES backtests(backtest_id)
);

CREATE TABLE IF NOT EXISTS walk_forward_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    window_index INTEGER NOT NULL,
    train_start DATETIME,
    train_end DATETIME,
    test_start DATETIME,
    test_end DATETIME,
    train_metric REAL,
    test_metric REAL,
    params_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES walk_forward_runs(run_id)
);

-- ============================================================
-- 6. RISK AND DECISION LOGS
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    risk_score REAL,
    position_size REAL,
    stop_distance REAL,
    take_profit_distance REAL,
    volatility_adj REAL,
    regime_adj REAL,
    is_approved INTEGER,
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES trade_candidates(id)
);

CREATE TABLE IF NOT EXISTS decision_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, -- SETUP, VALIDATION, RISK, EXECUTION, FILL, EXIT
    ref_id TEXT, -- candidate_id or trade_id
    market_snapshot_json TEXT,
    decision_json TEXT,
    outcome_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drift_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    drift_score REAL NOT NULL,
    drift_type TEXT, -- PSI, KL_DIV, MEAN_SHIFT
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
