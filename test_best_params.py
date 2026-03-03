import sys
from pathlib import Path

# Add the pack root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config.settings_trend as opt_settings
from src.strategy.module_trend import TrendStrategy
from src.strategy.backtester_trend import Backtester, analyze_trades, print_metrics

import pandas as pd
from src.utils.data_loader import load_train_data

print("Loading training data ONLY...")
ENTRY_DF, H1_REGIME, H4_STRUCTURE = load_train_data()

# Slice to the last 3 months of data
end_date = ENTRY_DF.index.max()
start_date = end_date - pd.DateOffset(months=3)
print(f"Filtering dataset to 3-month window: {start_date.date()} to {end_date.date()}")
ENTRY_DF = ENTRY_DF[ENTRY_DF.index >= start_date]
H1_REGIME = H1_REGIME[H1_REGIME.index >= start_date]
H4_STRUCTURE = H4_STRUCTURE[H4_STRUCTURE.index >= start_date]

# Apply the best parameters found
opt_settings.TREND_ATR_EXPANSION = 3.369402

# Restoring back to optimal
opt_settings.TREND_BREAKOUT_BARS = 78

opt_settings.TREND_RR_PRIMARY = 4.922755
# MANUALLY ADJUSTED: Reduced from 2.90 to 1.5 to activate the trailing stop much earlier
opt_settings.TREND_RR_TRAIL_ACTIVATION = 1.5

# MANUALLY ADJUSTED: Tightening RSI Long bounds to ensure stronger momentum
opt_settings.TREND_RSI_LONG_MIN = 55
opt_settings.TREND_RSI_LONG_MAX = 70

opt_settings.TREND_RSI_SHORT_MIN = 30
opt_settings.TREND_RSI_SHORT_MAX = 45

opt_settings.TREND_SL_ATR_MULT = 1.554308
opt_settings.TREND_USE_EMA_FILTER = False

print("Running Trend Strategy Module with refined RSI and 1.5R trailing stop...")
module = TrendStrategy("EURUSD")
signals = module.generate_signals(ENTRY_DF, H1_REGIME, H4_STRUCTURE)

if signals:
    print(f"Generated {len(signals)} signals.")
    
    bt = Backtester(
        spread_pips=0.2,
        slippage_max=0.3,
        use_trailing=True,
        check_regime_exit=True
    )
    trades = bt.simulate_trades(signals, ENTRY_DF, H1_REGIME)
    
    if trades:
        metrics = analyze_trades(trades, module.name)
        print_metrics(metrics)
    else:
        print("No trades were simulated.")
else:
    print("No signals generated.")
