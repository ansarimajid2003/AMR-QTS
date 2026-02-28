import sys
import os
from pathlib import Path
import itertools
import multiprocessing as mp

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CLEAN_DATA_DIR, MODELS_DIR, TRAIN_RATIO, SPREAD_PIPS, MAX_SLIPPAGE_PIPS
)
from src.regime.regime_detector import HMMRegimeDetector
from src.strategy.modules import (
    TrendStrategy, compute_indicators, detect_h4_structure,
)
from src.strategy.backtester import Backtester, analyze_trades, print_metrics


def load_data(symbol: str) -> dict:
    """Load all timeframes for a symbol."""
    data = {}
    for tf in ['15m', '1h', '4h', '1d']:
        path = os.path.join(CLEAN_DATA_DIR, f"{symbol}_{tf}.parquet")
        if os.path.exists(path):
            data[tf] = pd.read_parquet(path)
    return data

def run_single_backtest(args):
    """Run a single backtest with specific parameters."""
    symbol, train_entry, h1_regime, h4_structure, params = args
    
    # Temporarily override global settings needed for signal generation
    import config.settings as settings
    original_bars = settings.TREND_BREAKOUT_BARS
    original_atr = settings.TREND_ATR_EXPANSION
    original_long = settings.TREND_RSI_LONG_RANGE
    original_short = settings.TREND_RSI_SHORT_RANGE
    original_sl = settings.TREND_SL_ATR_MULT
    original_rr = settings.TREND_RR_PRIMARY

    try:
        settings.TREND_BREAKOUT_BARS = params['breakout_bars']
        settings.TREND_ATR_EXPANSION = params['atr_exp']
        settings.TREND_RSI_LONG_RANGE = params['rsi_long']
        settings.TREND_RSI_SHORT_RANGE = params['rsi_short']
        settings.TREND_SL_ATR_MULT = params['sl_atr']
        settings.TREND_RR_PRIMARY = params['rr']

        mod = TrendStrategy(symbol)
        signals = mod.generate_signals(train_entry, h1_regime, h4_structure)

        if not signals:
            return params, None

        bt = Backtester(
            spread_pips=SPREAD_PIPS.get(symbol, 0.2),
            slippage_max=MAX_SLIPPAGE_PIPS,
            use_trailing=True,
            check_regime_exit=True,
        )

        trades = bt.simulate_trades(signals, train_entry, h1_regime)
        if not trades:
            return params, None

        metrics = analyze_trades(trades, "TREND")
        return params, metrics

    finally:
        # Restore original settings
        settings.TREND_BREAKOUT_BARS = original_bars
        settings.TREND_ATR_EXPANSION = original_atr
        settings.TREND_RSI_LONG_RANGE = original_long
        settings.TREND_RSI_SHORT_RANGE = original_short
        settings.TREND_SL_ATR_MULT = original_sl
        settings.TREND_RR_PRIMARY = original_rr


def optimize_trend(symbol: str = "EURUSD"):
    print("=" * 65)
    print(f"AMR-QTS TREND MODULE OPTIMIZATION -- {symbol}")
    print("=" * 65)

    data = load_data(symbol)
    entry_df = data['15m']
    h1_df = data['1h']
    h4_df = data.get('4h', None)

    # 1. Setup Models
    model_path = os.path.join(MODELS_DIR, f"hmm_{symbol.lower()}.pkl")
    detector = HMMRegimeDetector.load(model_path)
    
    dxy_path = os.path.join(CLEAN_DATA_DIR, "DXY_1d.parquet")
    vix_path = os.path.join(CLEAN_DATA_DIR, "VIX_1d.parquet")
    dxy = pd.read_parquet(dxy_path) if os.path.exists(dxy_path) else None
    vix = pd.read_parquet(vix_path) if os.path.exists(vix_path) else None

    raw_feat = detector.feature_engine.compute_raw_features(h1_df, dxy, vix)
    norm_feat = detector.feature_engine.normalize(raw_feat)
    h1_regime = detector.predict(norm_feat)
    h4_structure = detect_h4_structure(h4_df)

    split_idx = int(len(entry_df) * TRAIN_RATIO)
    train_entry = entry_df.iloc[:split_idx]

    # Pre-compute indicators so we don't do it in loops
    train_entry = compute_indicators(train_entry)

    # 2. Define Parameter Grid
    grid = {
        'breakout_bars': [15, 20, 25],
        'atr_exp': [1.2, 1.5, 1.8],
        'rsi_long': [(45, 75), (50, 80)],
        'rsi_short': [(25, 55), (20, 50)],
        'sl_atr': [1.2, 1.5, 2.0],
        'rr': [1.5, 2.0, 2.5]
    }

    keys = grid.keys()
    combinations = list(itertools.product(*grid.values()))
    
    tasks = []
    for combo in combinations:
        params = dict(zip(keys, combo))
        tasks.append((symbol, train_entry, h1_regime, h4_structure, params))

    print(f"Total parameter combinations: {len(combinations)}")
    print(f"Running grid search using {mp.cpu_count()} cores...")

    results = []
    with mp.Pool(processes=mp.cpu_count()) as pool:
        for i, (params, metrics) in enumerate(pool.imap_unordered(run_single_backtest, tasks)):
            if metrics:
                results.append({
                    'params': params,
                    'trades': metrics['n_trades'],
                    'win_rate': metrics['win_rate'],
                    'pf': metrics['profit_factor'],
                    'sharpe': metrics['sharpe'],
                    'pnl': metrics['total_pnl_pips'],
                })
            
            if (i+1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(combinations)} combos evaluated...")

    # 3. Analyze Results
    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        print("No profitable combinations found.")
        return

    # Extract params to columns for easier viewing
    param_df = pd.json_normalize(res_df['params'])
    res_df = pd.concat([param_df, res_df.drop('params', axis=1)], axis=1)

    print("\nTop 10 by Profit Factor (Min 50 trades):")
    valid_res = res_df[res_df['trades'] >= 50].sort_values('pf', ascending=False)
    print(valid_res.head(10).to_string(index=False))

    print("\nTop 10 by Sharpe Ratio (Min 50 trades):")
    valid_res = valid_res.sort_values('sharpe', ascending=False)
    print(valid_res.head(10).to_string(index=False))


if __name__ == "__main__":
    np.random.seed(42)  # Reproducible slippage
    optimize_trend("EURUSD")
