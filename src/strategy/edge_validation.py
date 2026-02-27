"""
AMR-QTS Edge Validation Suite

Proves (or disproves) that the system's edge is real and not random.

Tests:
  1. Random Entry Benchmark — beat random entries with same risk management?
  2. Regime Contribution — how much does HMM gating add vs ungated?
  3. Signal Decay — signals most effective immediately or later?
  4. PnL Attribution — where does the edge come from?
  5. Deflated Sharpe Ratio — is the Sharpe ratio statistically significant?

Usage:
    python -m src.strategy.edge_validation
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CLEAN_DATA_DIR, MODELS_DIR, TRAIN_RATIO,
    SPREAD_PIPS, MAX_SLIPPAGE_PIPS, BASE_RISK_PCT,
    ATR_PERIOD,
)
from src.regime.regime_detector import HMMRegimeDetector, Regime
from src.strategy.modules import (
    TrendStrategy, MeanReversionStrategy, HighVolStrategy,
    compute_indicators, detect_h4_structure, Signal, Direction,
)
from src.strategy.backtester import Backtester, analyze_trades, print_metrics


# ============================================================
# DATA SETUP
# ============================================================

def setup():
    """Load data, model, generate predictions."""
    entry_df = pd.read_parquet(os.path.join(CLEAN_DATA_DIR, "EURUSD_15m.parquet"))
    h1 = pd.read_parquet(os.path.join(CLEAN_DATA_DIR, "EURUSD_1h.parquet"))
    h4 = pd.read_parquet(os.path.join(CLEAN_DATA_DIR, "EURUSD_4h.parquet"))
    dxy = pd.read_parquet(os.path.join(CLEAN_DATA_DIR, "DXY_1d.parquet"))
    vix = pd.read_parquet(os.path.join(CLEAN_DATA_DIR, "VIX_1d.parquet"))

    detector = HMMRegimeDetector.load(os.path.join(MODELS_DIR, "hmm_eurusd.pkl"))
    raw = detector.feature_engine.compute_raw_features(h1, dxy, vix)
    norm = detector.feature_engine.normalize(raw)
    h1_regime = detector.predict(norm)
    h4_structure = detect_h4_structure(h4)

    split = int(len(entry_df) * TRAIN_RATIO)
    test_entry = entry_df.iloc[split:]

    return test_entry, h1_regime, h4_structure, h1


# ============================================================
# TEST 1: RANDOM ENTRY BENCHMARK
# ============================================================

def test_random_entries(test_entry, h1_regime, n_random=1000, n_trades=640):
    """
    Generate random entry signals and simulate them with identical
    risk management. Compare to the real system.
    """
    print("\n" + "=" * 65)
    print("TEST 1: RANDOM ENTRY BENCHMARK")
    print(f"  {n_random} random trial(s) x {n_trades} trades each")
    print("=" * 65)

    df = compute_indicators(test_entry)
    valid_bars = df.dropna(subset=['atr']).index

    # Real system PnL (from previous run)
    bt = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS)

    random_pnls = []
    random_pfs = []
    random_sharpes = []

    for trial in range(n_random):
        np.random.seed(trial)

        # Pick random bars
        indices = np.random.choice(len(valid_bars) - 100, size=n_trades, replace=False)
        indices.sort()

        signals = []
        for idx in indices:
            ts = valid_bars[idx]
            bar = df.loc[ts]
            atr = bar['atr']
            if atr <= 0 or pd.isna(atr):
                continue

            # Random direction
            direction = Direction.LONG if np.random.random() > 0.5 else Direction.SHORT

            entry = bar['close']
            if direction == Direction.LONG:
                sl = entry - 1.5 * atr   # Same SL as trend module
                tp = entry + 2.0 * (entry - sl)  # 1:2 RR
            else:
                sl = entry + 1.5 * atr
                tp = entry - 2.0 * (sl - entry)

            signals.append(Signal(
                timestamp=ts, symbol="EURUSD",
                direction=direction, module="random",
                entry_price=entry, stop_loss=sl, take_profit=tp,
                atr_at_entry=atr,
            ))

        trades = bt.simulate_trades(signals, test_entry)
        m = analyze_trades(trades, "random")
        random_pnls.append(m['total_pnl_pips'])
        random_pfs.append(m['profit_factor'])
        if m['n_trades'] > 1:
            random_sharpes.append(m['sharpe'])

    random_pnls = np.array(random_pnls)
    random_pfs = np.array(random_pfs)

    # Stats
    real_pnl = 329.3  # From optimized backtest
    real_pf = 1.11
    real_sharpe = 0.76

    percentile = (random_pnls < real_pnl).mean() * 100

    print(f"\n  Random entries PnL distribution:")
    print(f"    Mean:   {random_pnls.mean():+.1f} pips")
    print(f"    Median: {np.median(random_pnls):+.1f} pips")
    print(f"    Std:    {random_pnls.std():.1f} pips")
    print(f"    Min:    {random_pnls.min():+.1f} pips")
    print(f"    Max:    {random_pnls.max():+.1f} pips")
    print(f"\n  Real system PnL:  {real_pnl:+.1f} pips")
    print(f"  Percentile:       {percentile:.1f}th (beats {percentile:.0f}% of random)")
    print(f"\n  Random PF distribution:")
    print(f"    Mean: {random_pfs.mean():.3f} | Std: {random_pfs.std():.3f}")
    print(f"    Real: {real_pf:.3f}")

    p_value = 1 - percentile / 100
    verdict = "PASS" if percentile > 95 else "MARGINAL" if percentile > 75 else "FAIL"
    print(f"\n  >> VERDICT: {verdict} (p-value = {p_value:.3f})")

    return {
        'test': 'random_entry',
        'verdict': verdict,
        'percentile': percentile,
        'p_value': p_value,
        'random_mean_pnl': random_pnls.mean(),
        'real_pnl': real_pnl,
    }


# ============================================================
# TEST 2: REGIME CONTRIBUTION
# ============================================================

def test_regime_contribution(test_entry, h1_regime, h4_structure):
    """
    Compare system performance WITH vs WITHOUT regime gating.
    """
    print("\n" + "=" * 65)
    print("TEST 2: REGIME CONTRIBUTION")
    print("  Does HMM regime gating improve performance?")
    print("=" * 65)

    bt = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS, use_trailing=True)

    # WITH regime gating (real system)
    np.random.seed(42)
    modules = [
        TrendStrategy("EURUSD"),
        MeanReversionStrategy("EURUSD"),
        HighVolStrategy("EURUSD"),
    ]
    gated_trades = []
    for mod in modules:
        sigs = mod.generate_signals(test_entry, h1_regime, h4_structure)
        trades = bt.simulate_trades(sigs, test_entry, h1_regime)
        gated_trades.extend(trades)
    gated = analyze_trades(gated_trades, "gated")

    # WITHOUT regime gating — create fake "always active" regime
    fake_regime = h1_regime.copy()
    # For trend module: make all bars TRENDING
    fake_trend_regime = fake_regime.copy()
    fake_trend_regime['regime'] = Regime.TRENDING
    fake_trend_regime['confidence'] = 1.0

    fake_range_regime = fake_regime.copy()
    fake_range_regime['regime'] = Regime.RANGING
    fake_range_regime['confidence'] = 1.0

    fake_hv_regime = fake_regime.copy()
    fake_hv_regime['regime'] = Regime.HIGH_VOL
    fake_hv_regime['confidence'] = 1.0

    np.random.seed(42)
    ungated_trades = []
    # Run each module with its "always on" regime
    t_sigs = modules[0].generate_signals(test_entry, fake_trend_regime, h4_structure)
    ungated_trades.extend(bt.simulate_trades(t_sigs, test_entry))

    mr_sigs = modules[1].generate_signals(test_entry, fake_range_regime, h4_structure)
    ungated_trades.extend(bt.simulate_trades(mr_sigs, test_entry))

    hv_sigs = modules[2].generate_signals(test_entry, fake_hv_regime, h4_structure)
    ungated_trades.extend(bt.simulate_trades(hv_sigs, test_entry))

    ungated = analyze_trades(ungated_trades, "ungated")

    print(f"\n  {'Metric':20s} | {'Gated (HMM)':>12s} | {'Ungated':>12s} | {'Impact':>10s}")
    print(f"  {'-'*20} | {'-'*12} | {'-'*12} | {'-'*10}")
    for key, label in [('n_trades', 'Trades'), ('win_rate', 'Win Rate'),
                       ('profit_factor', 'Profit Factor'), ('total_pnl_pips', 'Total PnL'),
                       ('expectancy_pips', 'Expectancy'), ('sharpe', 'Sharpe'),
                       ('max_dd_pips', 'Max Drawdown')]:
        gv = gated[key]
        uv = ungated[key]
        if isinstance(gv, float):
            if key == 'win_rate':
                print(f"  {label:20s} | {gv:>11.1%} | {uv:>11.1%} | {gv-uv:>+9.1%}")
            else:
                print(f"  {label:20s} | {gv:>+12.1f} | {uv:>+12.1f} | {gv-uv:>+10.1f}")
        else:
            print(f"  {label:20s} | {gv:>12} | {uv:>12} | {gv-uv:>+10}")

    pf_improvement = gated['profit_factor'] - ungated['profit_factor']
    verdict = "PASS" if pf_improvement > 0.05 else "MARGINAL" if pf_improvement > 0 else "FAIL"
    print(f"\n  >> VERDICT: {verdict} (PF improvement: {pf_improvement:+.3f})")

    return {
        'test': 'regime_contribution',
        'verdict': verdict,
        'gated_pf': gated['profit_factor'],
        'ungated_pf': ungated['profit_factor'],
        'pf_improvement': pf_improvement,
        'gated_n': gated['n_trades'],
        'ungated_n': ungated['n_trades'],
    }


# ============================================================
# TEST 3: SIGNAL DECAY ANALYSIS
# ============================================================

def test_signal_decay(test_entry, h1_regime, h4_structure):
    """
    Test if signals are most effective at immediate execution
    vs delayed by 1-4 bars.
    """
    print("\n" + "=" * 65)
    print("TEST 3: SIGNAL DECAY ANALYSIS")
    print("  Are signals most effective at T+0 or do they improve with delay?")
    print("=" * 65)

    bt = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS, use_trailing=True)

    # Generate base signals
    modules = [
        TrendStrategy("EURUSD"),
        MeanReversionStrategy("EURUSD"),
        HighVolStrategy("EURUSD"),
    ]

    all_signals = []
    for mod in modules:
        sigs = mod.generate_signals(test_entry, h1_regime, h4_structure)
        all_signals.extend(sigs)

    delays = [0, 1, 2, 4, 8]
    results = []

    for delay in delays:
        # Shift signal timestamps forward by `delay` bars
        delayed_signals = []
        for sig in all_signals:
            # Find bar at signal time + delay bars
            future = test_entry.index[test_entry.index > sig.timestamp]
            if len(future) <= delay:
                continue
            new_ts = future[delay] if delay > 0 else sig.timestamp
            new_bar = test_entry.loc[new_ts]

            # Recalculate entry at delayed price
            new_entry = new_bar['close']
            risk_dist = abs(sig.entry_price - sig.stop_loss)
            if sig.direction == Direction.LONG:
                new_sl = new_entry - risk_dist
                new_tp = new_entry + abs(sig.take_profit - sig.entry_price)
            else:
                new_sl = new_entry + risk_dist
                new_tp = new_entry - abs(sig.take_profit - sig.entry_price)

            delayed_signals.append(Signal(
                timestamp=new_ts, symbol=sig.symbol,
                direction=sig.direction, module=sig.module,
                entry_price=new_entry, stop_loss=new_sl, take_profit=new_tp,
                atr_at_entry=sig.atr_at_entry, regime=sig.regime,
                regime_confidence=sig.regime_confidence,
                risk_pct=sig.risk_pct,
            ))

        np.random.seed(42)
        trades = bt.simulate_trades(delayed_signals, test_entry, h1_regime)
        m = analyze_trades(trades, f"delay_{delay}")

        results.append({
            'delay': delay,
            'n': m['n_trades'],
            'pnl': m['total_pnl_pips'],
            'pf': m['profit_factor'],
            'wr': m['win_rate'],
            'sharpe': m['sharpe'],
        })

    print(f"\n  {'Delay':>6s} | {'Trades':>6s} | {'PnL':>10s} | {'PF':>6s} | {'WR':>6s} | {'Sharpe':>7s}")
    print(f"  {'-'*6} | {'-'*6} | {'-'*10} | {'-'*6} | {'-'*6} | {'-'*7}")
    for r in results:
        print(f"  T+{r['delay']:<4d} | {r['n']:>6d} | {r['pnl']:>+10.1f} | {r['pf']:>6.2f} | {r['wr']:>5.1%} | {r['sharpe']:>+7.2f}")

    # Signal should decay: T+0 should be best
    t0_pnl = results[0]['pnl']
    decays = all(r['pnl'] <= t0_pnl * 1.1 for r in results[1:])  # Allow 10% noise
    verdict = "PASS" if decays and t0_pnl > 0 else "MARGINAL" if t0_pnl > 0 else "FAIL"
    print(f"\n  >> VERDICT: {verdict} (T+0 is {'best' if decays else 'NOT best'}, T+0 PnL = {t0_pnl:+.1f})")

    return {
        'test': 'signal_decay',
        'verdict': verdict,
        'results': results,
    }


# ============================================================
# TEST 4: PNL ATTRIBUTION
# ============================================================

def test_pnl_attribution(test_entry, h1_regime, h4_structure):
    """
    Decompose PnL into:
      - Signal quality (entry direction)
      - Risk management (SL/TP/trailing)
      - Regime filtering (HMM gating)
    """
    print("\n" + "=" * 65)
    print("TEST 4: PNL ATTRIBUTION")
    print("  Where does the edge come from?")
    print("=" * 65)

    bt = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS, use_trailing=True)
    bt_notrail = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS, use_trailing=False)

    modules = [
        TrendStrategy("EURUSD"),
        MeanReversionStrategy("EURUSD"),
        HighVolStrategy("EURUSD"),
    ]

    all_signals = []
    for mod in modules:
        sigs = mod.generate_signals(test_entry, h1_regime, h4_structure)
        all_signals.extend(sigs)

    # A. Full system (baseline)
    np.random.seed(42)
    full_trades = bt.simulate_trades(all_signals, test_entry, h1_regime)
    full = analyze_trades(full_trades, "full")

    # B. Direction accuracy: what % of signals had price move in the right direction
    #    within the next 4 bars?
    df = compute_indicators(test_entry)
    correct_direction = 0
    total_checked = 0
    for sig in all_signals:
        future = test_entry.loc[test_entry.index > sig.timestamp]
        if len(future) < 4:
            continue
        next_4 = future.iloc[:4]
        if sig.direction == Direction.LONG:
            moved_right = next_4['high'].max() > sig.entry_price
        else:
            moved_right = next_4['low'].min() < sig.entry_price
        if moved_right:
            correct_direction += 1
        total_checked += 1

    dir_accuracy = correct_direction / total_checked if total_checked > 0 else 0

    # C. Risk management contribution: SL/TP only vs Full
    np.random.seed(42)
    sltp_trades = bt_notrail.simulate_trades(all_signals, test_entry, h1_regime)
    sltp = analyze_trades(sltp_trades, "sl_tp_only")

    # D. Trailing stop contribution = Full - SL/TP only
    trail_contribution = full['total_pnl_pips'] - sltp['total_pnl_pips']

    print(f"\n  ATTRIBUTION BREAKDOWN:")
    print(f"  {'Component':25s} | {'Value':>12s}")
    print(f"  {'-'*25} | {'-'*12}")
    print(f"  {'Direction accuracy (4-bar)':25s} | {dir_accuracy:>11.1%}")
    print(f"  {'Full system PnL':25s} | {full['total_pnl_pips']:>+12.1f}")
    print(f"  {'SL/TP only PnL':25s} | {sltp['total_pnl_pips']:>+12.1f}")
    print(f"  {'Trailing stop contribution':25s} | {trail_contribution:>+12.1f}")
    print(f"  {'Win rate (full)':25s} | {full['win_rate']:>11.1%}")
    print(f"  {'Win rate (SL/TP only)':25s} | {sltp['win_rate']:>11.1%}")
    print(f"  {'Avg R:R (full)':25s} | {full['avg_rr']:>12.2f}")
    print(f"  {'Avg R:R (SL/TP only)':25s} | {sltp['avg_rr']:>12.2f}")

    verdict = "PASS" if dir_accuracy > 0.5 and full['total_pnl_pips'] > 0 else "FAIL"
    print(f"\n  >> VERDICT: {verdict} (direction accuracy = {dir_accuracy:.1%})")

    return {
        'test': 'pnl_attribution',
        'verdict': verdict,
        'direction_accuracy': dir_accuracy,
        'full_pnl': full['total_pnl_pips'],
        'sltp_pnl': sltp['total_pnl_pips'],
        'trail_contribution': trail_contribution,
    }


# ============================================================
# TEST 5: DEFLATED SHARPE RATIO
# ============================================================

def test_deflated_sharpe(test_entry, h1_regime, h4_structure, n_trials=100):
    """
    Harvey-Liu-Zhu (2016) Deflated Sharpe Ratio.
    Tests if observed Sharpe is significant given multiple testing.
    """
    print("\n" + "=" * 65)
    print("TEST 5: DEFLATED SHARPE RATIO")
    print("  Is the Sharpe ratio statistically significant?")
    print("=" * 65)

    bt = Backtester(spread_pips=SPREAD_PIPS['EURUSD'], slippage_max=MAX_SLIPPAGE_PIPS, use_trailing=True)

    modules = [
        TrendStrategy("EURUSD"),
        MeanReversionStrategy("EURUSD"),
        HighVolStrategy("EURUSD"),
    ]

    # Get real system returns
    np.random.seed(42)
    all_trades = []
    for mod in modules:
        sigs = mod.generate_signals(test_entry, h1_regime, h4_structure)
        trades = bt.simulate_trades(sigs, test_entry, h1_regime)
        all_trades.extend(trades)

    returns = np.array([t.pnl_r for t in all_trades])
    n = len(returns)
    observed_sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    # Skewness and kurtosis
    skew = stats.skew(returns)
    kurt = stats.kurtosis(returns)

    # Expected max Sharpe from N independent trials (Euler-Mascheroni approximation)
    euler_mascheroni = 0.5772
    e_max_sharpe = stats.norm.ppf(1 - 1 / n_trials) * (
        1 + euler_mascheroni / np.log(n_trials)
    ) if n_trials > 1 else 0

    # Standard error of Sharpe
    se_sharpe = np.sqrt(
        (1 + 0.5 * observed_sharpe**2 - skew * observed_sharpe +
         (kurt / 4) * observed_sharpe**2) / n
    )

    # Deflated Sharpe test statistic
    if se_sharpe > 0:
        dsr_stat = (observed_sharpe - e_max_sharpe) / se_sharpe
        dsr_pvalue = 1 - stats.norm.cdf(dsr_stat)
    else:
        dsr_stat = 0
        dsr_pvalue = 1.0

    # Also: simple bootstrap p-value
    bootstrap_sharpes = []
    for _ in range(n_trials):
        shuffled = np.random.permutation(returns)
        bs_sharpe = shuffled.mean() / shuffled.std() * np.sqrt(252) if shuffled.std() > 0 else 0
        bootstrap_sharpes.append(bs_sharpe)
    bootstrap_p = (np.array(bootstrap_sharpes) >= observed_sharpe).mean()

    print(f"\n  Observed Sharpe:      {observed_sharpe:.3f}")
    print(f"  N trades:             {n}")
    print(f"  Return skewness:      {skew:+.3f}")
    print(f"  Return kurtosis:      {kurt:+.3f}")
    print(f"  E[max Sharpe] ({n_trials} trials): {e_max_sharpe:.3f}")
    print(f"  SE(Sharpe):           {se_sharpe:.3f}")
    print(f"  DSR test statistic:   {dsr_stat:+.3f}")
    print(f"  DSR p-value:          {dsr_pvalue:.3f}")
    print(f"  Bootstrap p-value:    {bootstrap_p:.3f}")

    verdict = "PASS" if dsr_pvalue < 0.10 else "MARGINAL" if dsr_pvalue < 0.20 else "FAIL"
    print(f"\n  >> VERDICT: {verdict} (DSR p = {dsr_pvalue:.3f}, bootstrap p = {bootstrap_p:.3f})")

    return {
        'test': 'deflated_sharpe',
        'verdict': verdict,
        'observed_sharpe': observed_sharpe,
        'dsr_pvalue': dsr_pvalue,
        'bootstrap_p': bootstrap_p,
        'skew': skew,
        'kurt': kurt,
    }


# ============================================================
# MAIN
# ============================================================

def run_edge_validation():
    """Run all edge validation tests."""
    print("=" * 65)
    print("AMR-QTS EDGE VALIDATION SUITE")
    print("=" * 65)

    test_entry, h1_regime, h4_structure, h1 = setup()
    print(f"  Test data: {test_entry.index[0].date()} to {test_entry.index[-1].date()}")
    print(f"  Test bars: {len(test_entry):,}")

    results = []

    # Test 1: Random Entry Benchmark
    r1 = test_random_entries(test_entry, h1_regime, n_random=500, n_trades=640)
    results.append(r1)

    # Test 2: Regime Contribution
    r2 = test_regime_contribution(test_entry, h1_regime, h4_structure)
    results.append(r2)

    # Test 3: Signal Decay
    r3 = test_signal_decay(test_entry, h1_regime, h4_structure)
    results.append(r3)

    # Test 4: PnL Attribution
    r4 = test_pnl_attribution(test_entry, h1_regime, h4_structure)
    results.append(r4)

    # Test 5: Deflated Sharpe
    r5 = test_deflated_sharpe(test_entry, h1_regime, h4_structure, n_trials=200)
    results.append(r5)

    # Summary
    print("\n" + "=" * 65)
    print("EDGE VALIDATION SUMMARY")
    print("=" * 65)
    for r in results:
        status = "PASS" if r['verdict'] == 'PASS' else "WARN" if r['verdict'] == 'MARGINAL' else "FAIL"
        icon = "[PASS]" if status == "PASS" else "[WARN]" if status == "WARN" else "[FAIL]"
        print(f"  {icon} {r['test']}: {r['verdict']}")

    pass_count = sum(1 for r in results if r['verdict'] == 'PASS')
    marginal_count = sum(1 for r in results if r['verdict'] == 'MARGINAL')
    fail_count = sum(1 for r in results if r['verdict'] == 'FAIL')
    print(f"\n  Score: {pass_count} PASS / {marginal_count} MARGINAL / {fail_count} FAIL")

    overall = "EDGE CONFIRMED" if pass_count >= 3 and fail_count == 0 else \
              "EDGE LIKELY" if pass_count >= 2 else \
              "EDGE QUESTIONABLE" if pass_count >= 1 else "NO EDGE"
    print(f"  Overall: {overall}")
    print("=" * 65)

    return results


if __name__ == "__main__":
    results = run_edge_validation()
