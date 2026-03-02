import sys
import os
from pathlib import Path

# Add the pack root to sys.path so imports work flawlessly
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from config.settings import SPREAD_PIPS, MAX_SLIPPAGE_PIPS
from src.strategy.modules import TrendStrategy, MeanReversionStrategy, HighVolStrategy
from src.strategy.backtester import Backtester, analyze_trades, print_metrics
from src.regime.regime_detector import Regime

def load_data():
    print("Loading AI Optimization Dataset...")
    data_dir = os.path.join(PROJECT_ROOT, "data")
    
    entry_file = os.path.join(data_dir, "EURUSD_15m.csv")
    h1_file = os.path.join(data_dir, "EURUSD_h1_regime.csv")
    h4_file = os.path.join(data_dir, "EURUSD_h4_structure.csv")
    
    if not all(os.path.exists(f) for f in [entry_file, h1_file, h4_file]):
        print(f"Data files missing from {data_dir}. Make sure data was copied.")
        sys.exit(1)
        
    entry_df = pd.read_csv(entry_file, index_col=0, parse_dates=True)
    h1_regime = pd.read_csv(h1_file, index_col=0, parse_dates=True)
    h4_structure = pd.read_csv(h4_file, index_col=0, parse_dates=True)
    
    # Convert regime string values back to Enum objects (as required by the backtester internals)
    h1_regime['regime'] = h1_regime['regime'].apply(
        lambda x: Regime[x] if isinstance(x, str) and x in Regime.__members__ else x
    )
    
    # H4 structure logic expects a pandas Series, not a DataFrame
    h4_structure_series = h4_structure['structure']
    
    return entry_df, h1_regime, h4_structure_series

def run_backtest():
    entry_df, h1_regime, h4_structure = load_data()
    print(f"Loaded {len(entry_df)} 15m candles.")
    
    modules = [
        TrendStrategy("EURUSD"),
        MeanReversionStrategy("EURUSD"),
        HighVolStrategy("EURUSD")
    ]
    
    # Instantiate the backtester
    bt = Backtester(
        spread_pips=0.2,
        slippage_max=0.3,
        use_trailing=True,
        check_regime_exit=True
    )

    all_trades = []
    
    for mod in modules:
        print(f"\n>> Testing {mod.name.upper()} Module...")
        signals = mod.generate_signals(entry_df, h1_regime, h4_structure)
        
        if signals:
            trades = bt.simulate_trades(signals, entry_df, h1_regime)
            metrics = analyze_trades(trades, mod.name)
            print_metrics(metrics)
            all_trades.extend(trades)
        else:
            print("No signals generated.")

    if all_trades:
        print("\n" + "="*50)
        combined = analyze_trades(all_trades, "COMBINED SYSTEM")
        print_metrics(combined)

if __name__ == "__main__":
    np.random.seed(42)  # For reproducible slippage results between tests
    run_backtest()
