from .spec import AssetClass, InstrumentSpec

GOLD_XAUUSD = InstrumentSpec(
    symbol="XAUUSD",
    asset_class=AssetClass.CFD,
    venue="Pepperstone",
    tick_size=0.01,
    point_value=1.0, # 1 point ($1) = $1 at 1.0 lot
    contract_size=100.0, # 1 lot = 100 oz
    min_lot=0.01,
    lot_step=0.01,
    base_currency="USD",
    leverage_max=20.0, 
    commission_per_lot=0.0, # Spread-based
    spread_base=0.15, # 15 pips average
    swap_long=-8.5, # Daily cost per lot
    swap_short=2.1,
    trading_hours={"mon-fri": ["00:01-23:59"]}
)

US500_CASH = InstrumentSpec(
    symbol="US500",
    asset_class=AssetClass.CFD,
    venue="ICMarkets",
    tick_size=0.1,
    point_value=1.0,
    contract_size=10.0,
    min_lot=0.1,
    lot_step=0.1,
    base_currency="USD",
    leverage_max=10.0,
    commission_per_lot=0.0,
    spread_base=0.5,
    swap_long=-2.4,
    swap_short=-1.1,
    trading_hours={"mon-fri": ["00:01-23:59"]}
)

AAPL_STOCK = InstrumentSpec(
    symbol="AAPL",
    asset_class=AssetClass.STOCK,
    venue="NASDAQ",
    tick_size=0.01,
    point_value=1.0,
    contract_size=1.0,
    min_lot=1.0,
    lot_step=1.0,
    base_currency="USD",
    leverage_max=2.0,
    commission_per_lot=0.02, # $0.02 per share
    spread_base=0.05,
    swap_long=-0.01, # Simplified overnight cost
    swap_short=0.0,
    allow_overnight=True,
    allow_short=True,
    trading_hours={"mon-fri": ["14:30-21:00"]} # US Eastern in UTC (approx)
)
