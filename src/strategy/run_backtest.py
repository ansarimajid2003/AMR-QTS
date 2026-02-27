"""
AMR-QTS Isolated Backtest — Phase 1 Step 4

Runs each strategy module independently on EURUSD data, with HMM regime
gating, and reports per-module performance metrics.

Usage:
    python -m src.strategy.run_backtest
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CLEAN_DATA_DIR, MODELS_DIR, TRAIN_RATIO, SPREAD_PIPS,
    MAX_SLIPPAGE_PIPS, MIN_PROFIT_FACTOR, MAX_DRAWDOWN_PCT,
    MIN_WIN_RATE, MIN_SHARPE,
)
from src.regime.regime_detector import HMMRegimeDetector, RegimeFeatureEngine, Regime
from src.strategy.modules import (
    TrendStrategy, MeanReversionStrategy, HighVolStrategy,
    compute_indicators, detect_h4_structure,
)
from src.strategy.backtester import Backtester, analyze_trades, print_metrics


def load_data(symbol: str) -> dict:
    """Load all timeframes for a symbol."""
    data = {}
    for tf in ['15m', '1h', '4h', '1d']:
        # Try clean data first
        path = os.path.join(CLEAN_DATA_DIR, f"{symbol}_{tf.replace('m','m').replace('h','h')}.parquet")
        if not os.path.exists(path):
            # Try alternative naming
            alt = tf.replace('15m', '15m').replace('1h', '1h').replace('4h', '4h').replace('1d', '1d')
            path = os.path.join(CLEAN_DATA_DIR, f"{symbol}_{alt}.parquet")
        if os.path.exists(path):
            data[tf] = pd.read_parquet(path)
            print(f"  {tf}: {len(data[tf]):,} bars ({data[tf].index[0].date()} to {data[tf].index[-1].date()})")
        else:
            print(f"  {tf}: NOT FOUND at {path}")
    return data


def run_backtest(symbol: str = "EURUSD"):
    """Run isolated backtest for all modules on one symbol."""
    print("=" * 65)
    print(f"AMR-QTS ISOLATED BACKTEST -- {symbol}")
    print("=" * 65)

    # 1. Load data
    print(f"\n[1] Loading data for {symbol}...")
    data = load_data(symbol)

    if '15m' not in data or '1h' not in data:
        print("[ERROR] Missing required data (15m, 1h)")
        return

    entry_df = data['15m']
    h1_df = data['1h']
    h4_df = data.get('4h', None)

    # 2. Load HMM and predict regimes
    print(f"\n[2] Loading HMM regime detector...")
    model_path = os.path.join(MODELS_DIR, f"hmm_{symbol.lower()}.pkl")
    if not os.path.exists(model_path):
        print(f"[ERROR] No HMM model at {model_path}")
        return

    detector = HMMRegimeDetector.load(model_path)

    # Load cross-asset
    dxy_path = os.path.join(CLEAN_DATA_DIR, "DXY_1d.parquet")
    vix_path = os.path.join(CLEAN_DATA_DIR, "VIX_1d.parquet")
    dxy = pd.read_parquet(dxy_path) if os.path.exists(dxy_path) else None
    vix = pd.read_parquet(vix_path) if os.path.exists(vix_path) else None

    # Compute features and predict
    raw_feat = detector.feature_engine.compute_raw_features(h1_df, dxy, vix)
    norm_feat = detector.feature_engine.normalize(raw_feat)
    h1_regime = detector.predict(norm_feat)
    print(f"  Regime predictions: {len(h1_regime):,} H1 bars")

    # Regime distribution
    for r in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL]:
        pct = (h1_regime['regime'] == r).sum() / len(h1_regime) * 100
        print(f"    {r.name}: {pct:.1f}%")

    # 3. H4 structure
    print(f"\n[3] Detecting H4 structure...")
    if h4_df is not None:
        h4_structure = detect_h4_structure(h4_df)
        print(f"  H4 structure: {len(h4_structure):,} bars")
        up = (h4_structure == 1).sum()
        dn = (h4_structure == -1).sum()
        print(f"    Uptrend: {up} | Downtrend: {dn}")
    else:
        h4_structure = pd.Series(0, index=h1_df.index)
        print(f"  [WARN] No H4 data, using neutral structure")

    # 4. Train/test split on entry data
    split_idx = int(len(entry_df) * TRAIN_RATIO)
    test_entry = entry_df.iloc[split_idx:]
    print(f"\n[4] Test period: {test_entry.index[0].date()} to {test_entry.index[-1].date()} "
          f"({len(test_entry):,} 15m bars)")

    # 5. Generate signals for each module
    print(f"\n[5] Generating signals on TEST data...")
    modules = [
        TrendStrategy(symbol),
        MeanReversionStrategy(symbol),
        HighVolStrategy(symbol),
    ]

    all_trades = []
    bt = Backtester(
        spread_pips=SPREAD_PIPS.get(symbol, 0.2),
        slippage_max=MAX_SLIPPAGE_PIPS,
        use_trailing=True,
        check_regime_exit=True,
    )

    for mod in modules:
        print(f"\n  >> {mod.name.upper()}")
        signals = mod.generate_signals(test_entry, h1_regime, h4_structure)
        print(f"     Signals generated: {len(signals)}")

        if signals:
            # Show signal distribution
            longs = sum(1 for s in signals if s.direction == 1)
            shorts = len(signals) - longs
            print(f"     Long: {longs} | Short: {shorts}")

            # Simulate trades
            trades = bt.simulate_trades(signals, test_entry, h1_regime)
            print(f"     Trades completed: {len(trades)}")

            # Performance metrics
            metrics = analyze_trades(trades, mod.name)
            print_metrics(metrics)

            all_trades.extend(trades)

    # 6. Combined system performance
    if all_trades:
        print(f"\n{'=' * 65}")
        combined = analyze_trades(all_trades, "COMBINED SYSTEM")
        print_metrics(combined)

        # Pass/Fail check
        print(f"\n  VALIDATION CHECKS:")
        checks = [
            ("Profit Factor > 1.3", combined['profit_factor'] > MIN_PROFIT_FACTOR),
            ("Win Rate > 40%", combined['win_rate'] > MIN_WIN_RATE),
            ("Sharpe > 0.8", combined['sharpe'] > MIN_SHARPE),
            ("Expectancy > 0", combined['expectancy_pips'] > 0),
        ]
        for label, passed in checks:
            status = "PASS" if passed else "FAIL"
            print(f"    [{status}] {label}")

        pass_count = sum(1 for _, p in checks if p)
        print(f"\n  Score: {pass_count}/{len(checks)} checks passed")

    print(f"\n{'=' * 65}")
    return all_trades


if __name__ == "__main__":
    np.random.seed(42)  # Reproducible slippage
    trades = run_backtest("EURUSD")
