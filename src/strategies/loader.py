from src.strategies.registry import StrategyRouter
from src.core.contracts.spec import ContractManager, InstrumentSpec

# Breakout
from src.strategies.breakout.donchian import DonchianBreakout
from src.strategies.breakout.orb import OpeningRangeBreakout
from src.strategies.breakout.volatility_compression import VolatilityCompressionBreakout
from src.strategies.breakout.breakout_retest import BreakoutRetest
from src.strategies.breakout.imbalance import ImbalanceBreakout

# Pullback
from src.strategies.pullback.ema_pullback import EMAPullback
from src.strategies.pullback.vwap_pullback import VWAPPullback
from src.strategies.pullback.fib_pullback import FibPullback
from src.strategies.pullback.smc import SMCPullback

# Mean Reversion
from src.strategies.mean_reversion.bollinger_mr import BollingerMeanReversion
from src.strategies.mean_reversion.zscore_mr import ZScoreMeanReversion
from src.strategies.mean_reversion.vwap_reversion import VWAPReversion

# Range
from src.strategies.range.range_fade import RangeFade
from src.strategies.range.sr_fade import SRFade

# Gap
from src.strategies.gap.gap_and_go import GapAndGo
from src.strategies.gap.gap_fill import GapFill
from src.strategies.gap.gap_fade import GapFade

# Trend
from src.strategies.trend.trend_follower import TrendFollower
from src.strategies.trend.lifecycle_trend import LifecycleTrendStrategy

def create_default_router(contract_manager: ContractManager, spec: InstrumentSpec) -> StrategyRouter:
    router = StrategyRouter(contract_manager)
    
    # Register all strategies
    router.register_strategy(DonchianBreakout(spec))
    router.register_strategy(OpeningRangeBreakout(spec))
    router.register_strategy(VolatilityCompressionBreakout(spec))
    router.register_strategy(BreakoutRetest(spec))
    router.register_strategy(ImbalanceBreakout(spec))
    
    router.register_strategy(EMAPullback(spec))
    router.register_strategy(VWAPPullback(spec))
    router.register_strategy(FibPullback(spec))
    router.register_strategy(SMCPullback(spec))
    
    router.register_strategy(TrendFollower(spec))
    router.register_strategy(LifecycleTrendStrategy(spec))
    
    router.register_strategy(BollingerMeanReversion(spec))
    router.register_strategy(ZScoreMeanReversion(spec))
    router.register_strategy(VWAPReversion(spec))
    
    router.register_strategy(RangeFade(spec))
    router.register_strategy(SRFade(spec))
    
    router.register_strategy(GapAndGo(spec))
    router.register_strategy(GapFill(spec))
    router.register_strategy(GapFade(spec))
    
    return router
