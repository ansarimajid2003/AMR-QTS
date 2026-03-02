import sys
from pathlib import Path

# Add the pack root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config.settings as opt_settings
from src.strategy.modules import MeanReversionStrategy
from src.strategy.backtester import Backtester, analyze_trades, print_metrics

from ai_optimization_pack.run_optimization import load_data

print("Loading data...")
ENTRY_DF, H1_REGIME, H4_STRUCTURE = load_data()

# Apply the best parameters found
opt_settings.MR_BB_PERIOD = 41
opt_settings.MR_BB_STD = 1.6549
opt_settings.MR_MIN_RR = 1.6178
opt_settings.MR_RSI_OVERBOUGHT = 63.0000
opt_settings.MR_RSI_OVERSOLD = 35.0000
opt_settings.MR_RSI_PERIOD = 21
opt_settings.MR_SL_ATR_MULT = 2.1589
opt_settings.MR_TIME_EXIT_BARS = 26

print("Running Mean Reversion Strategy Module with optimal parameters...")
module = MeanReversionStrategy("EURUSD")
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
