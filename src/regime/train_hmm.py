"""
AMR-QTS HMM Regime Detector — Training & Diagnostics

Trains the HMM on EURUSD H1 data (8 years), generates diagnostic
visualizations, and saves the model for live use.

Usage:
    python -m src.regime.train_hmm
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CLEAN_DATA_DIR, MODELS_DIR, LOGS_DIR, TRAIN_RATIO,
    HMM_N_STATES, HMM_MIN_CONFIDENCE,
)
from src.regime.regime_detector import (
    RegimeFeatureEngine, HMMRegimeDetector, RuleBasedDetector, Regime,
)


# ============================================================
# DATA LOADING
# ============================================================

def load_h1_data(symbol: str) -> pd.DataFrame:
    """Load cleaned H1 data."""
    path = os.path.join(CLEAN_DATA_DIR, f"{symbol}_1h.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No H1 data at {path}")
    df = pd.read_parquet(path)
    print(f"  Loaded {symbol} H1: {len(df):,} bars "
          f"({df.index[0].date()} to {df.index[-1].date()})")
    return df


def load_cross_asset() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load DXY and VIX daily data."""
    dxy_path = os.path.join(CLEAN_DATA_DIR, "DXY_1d.parquet")
    vix_path = os.path.join(CLEAN_DATA_DIR, "VIX_1d.parquet")

    dxy = None
    vix = None

    if os.path.exists(dxy_path):
        dxy = pd.read_parquet(dxy_path)
        print(f"  Loaded DXY daily: {len(dxy):,} bars")
    else:
        print(f"  [WARN] No DXY data at {dxy_path}")

    if os.path.exists(vix_path):
        vix = pd.read_parquet(vix_path)
        print(f"  Loaded VIX daily: {len(vix):,} bars")
    else:
        print(f"  [WARN] No VIX data at {vix_path}")

    return dxy, vix


# ============================================================
# TRAINING
# ============================================================

def train_hmm(symbol: str = "EURUSD"):
    """Main training pipeline."""
    print("=" * 60)
    print("AMR-QTS HMM REGIME DETECTOR — TRAINING")
    print("=" * 60)

    # 1. Load data
    print("\n[1] Loading data...")
    h1_df = load_h1_data(symbol)
    dxy_daily, vix_daily = load_cross_asset()

    # 2. Feature engineering
    print("\n[2] Computing features...")
    engine = RegimeFeatureEngine()
    raw_features = engine.compute_raw_features(h1_df, dxy_daily, vix_daily)
    print(f"  Features computed: {len(raw_features):,} bars × {len(engine.FEATURE_NAMES)} features")
    print(f"  Feature range: {raw_features.index[0].date()} to {raw_features.index[-1].date()}")

    # Show raw feature statistics
    print("\n  Raw feature stats:")
    stats = raw_features.describe().T[['mean', 'std', 'min', 'max']]
    for name, row in stats.iterrows():
        print(f"    {name:18s}  mean={row['mean']:+.5f}  std={row['std']:.5f}  "
              f"range=[{row['min']:+.5f}, {row['max']:+.5f}]")

    # 3. Train/test split
    print(f"\n[3] Train/test split ({TRAIN_RATIO:.0%}/{1-TRAIN_RATIO:.0%})...")
    split_idx = int(len(raw_features) * TRAIN_RATIO)
    train_raw = raw_features.iloc[:split_idx]
    test_raw = raw_features.iloc[split_idx:]
    print(f"  Train: {len(train_raw):,} bars ({train_raw.index[0].date()} to {train_raw.index[-1].date()})")
    print(f"  Test:  {len(test_raw):,} bars ({test_raw.index[0].date()} to {test_raw.index[-1].date()})")

    # 4. Normalize features (fit on train)
    train_norm = engine.fit_normalize(train_raw)
    test_norm = engine.normalize(test_raw)

    # 5. Fit HMM
    print(f"\n[4] Training GaussianHMM (n_states={HMM_N_STATES}, covariance=full)...")
    detector = HMMRegimeDetector()
    detector.feature_engine = engine
    detector.fit(train_norm)

    train_ll = detector.score(train_norm)
    test_ll = detector.score(test_norm)
    print(f"  Train log-likelihood: {train_ll:.1f}")
    print(f"  Test  log-likelihood: {test_ll:.1f}")
    print(f"  Converged: {detector.hmm.monitor_.converged}")

    # 6. Auto-labeled states
    print(f"\n[5] State labeling:")
    print(f"  State map: {detector.state_map_}")
    for hmm_state, regime in detector.state_map_.items():
        print(f"    HMM state {hmm_state} → {regime.name}")

    # 7. Transition matrix
    print(f"\n[6] Transition matrix:")
    trans = detector.get_transition_matrix()
    print(trans.to_string(float_format='{:.3f}'.format))

    # 8. Predict on full dataset
    print(f"\n[7] Predicting regimes...")
    all_norm = pd.concat([train_norm, test_norm])
    predictions = detector.predict(all_norm)

    # Regime statistics
    print(f"\n[8] Regime statistics:")
    regime_names = {Regime.TRENDING: 'TRENDING', Regime.RANGING: 'RANGING',
                    Regime.HIGH_VOL: 'HIGH_VOL', Regime.NEUTRAL: 'NEUTRAL'}

    for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL, Regime.NEUTRAL]:
        mask = predictions['regime'] == regime
        count = mask.sum()
        pct = count / len(predictions) * 100
        if count > 0:
            avg_conf = predictions.loc[mask, 'confidence'].mean()
            # Calculate average regime duration (consecutive bars)
            changes = (predictions['regime'] != predictions['regime'].shift(1))
            regime_starts = changes & mask
            n_segments = max(regime_starts.sum(), 1)
            avg_duration = count / n_segments
            print(f"  {regime_names[regime]:10s}: {count:6,} bars ({pct:5.1f}%) "
                  f"| avg conf: {avg_conf:.2f} | avg duration: {avg_duration:.1f} bars")
        else:
            print(f"  {regime_names[regime]:10s}: {count:6,} bars ({pct:5.1f}%)")

    # Check for degenerate states
    for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL]:
        pct = (predictions['regime'] == regime).sum() / len(predictions) * 100
        if pct < 5:
            print(f"  [WARN] {regime_names[regime]} captures only {pct:.1f}% of bars (< 5% threshold)")

    # 9. Rule-based comparison
    print(f"\n[9] Rule-based detector comparison...")
    h1_aligned = h1_df.loc[predictions.index]
    rules = RuleBasedDetector()
    rule_preds = rules.predict(h1_aligned)

    # Agreement rate
    hmm_regimes = predictions['regime'].values
    rule_regimes = rule_preds['regime'].values
    # Only compare where both have a valid regime (not NEUTRAL)
    valid = (hmm_regimes != Regime.NEUTRAL) & (rule_regimes != Regime.NEUTRAL)
    if valid.sum() > 0:
        agreement = (hmm_regimes[valid] == rule_regimes[valid]).mean() * 100
        print(f"  Agreement rate (excluding NEUTRAL): {agreement:.1f}%")
    else:
        print(f"  [WARN] No non-NEUTRAL bars to compare")

    # Rule-based regime distribution
    for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL, Regime.NEUTRAL]:
        count = (rule_regimes == regime).sum()
        pct = count / len(rule_regimes) * 100
        print(f"  Rules {regime_names[regime]:10s}: {count:6,} bars ({pct:5.1f}%)")

    # 10. Save model
    print(f"\n[10] Saving model...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = os.path.join(MODELS_DIR, f"hmm_{symbol.lower()}.pkl")
    detector.save(model_path)
    model_size = os.path.getsize(model_path) / 1024
    print(f"  Saved: {model_path} ({model_size:.1f} KB)")

    # 11. Generate diagnostics
    print(f"\n[11] Generating diagnostic plots...")
    os.makedirs(LOGS_DIR, exist_ok=True)
    _plot_regime_overlay(h1_aligned, predictions, symbol)
    _plot_regime_stats(predictions, trans, symbol)
    _plot_feature_distributions(all_norm, predictions, symbol)

    # 12. Summary
    print(f"\n{'=' * 60}")
    print("TRAINING COMPLETE")
    print(f"  Model: {model_path}")
    print(f"  Diagnostics: {LOGS_DIR}/")
    print(f"  States: {HMM_N_STATES}")
    print(f"  Train log-LL: {train_ll:.1f}")
    print(f"  Test log-LL:  {test_ll:.1f}")
    print(f"  HMM vs Rules agreement: {agreement:.1f}%" if valid.sum() > 0 else "")
    print(f"{'=' * 60}")

    return detector, predictions


# ============================================================
# DIAGNOSTIC PLOTS
# ============================================================

REGIME_COLORS = {
    Regime.TRENDING: '#2196F3',   # Blue
    Regime.RANGING: '#FF9800',    # Orange
    Regime.HIGH_VOL: '#F44336',   # Red
    Regime.NEUTRAL: '#9E9E9E',    # Grey
}

REGIME_LABELS = {
    Regime.TRENDING: 'Trending',
    Regime.RANGING: 'Ranging',
    Regime.HIGH_VOL: 'High Vol',
    Regime.NEUTRAL: 'Neutral',
}


def _plot_regime_overlay(
    h1_df: pd.DataFrame,
    predictions: pd.DataFrame,
    symbol: str,
):
    """Plot price chart with colored regime background bands."""
    fig, axes = plt.subplots(3, 1, figsize=(20, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
    fig.suptitle(f'{symbol} HMM Regime Classification', fontsize=16, fontweight='bold')

    # --- Panel 1: Price + regime background ---
    ax = axes[0]
    price = h1_df['close'].loc[predictions.index]
    ax.plot(price.index, price.values, color='black', linewidth=0.5, alpha=0.8)

    # Color background by regime
    regimes = predictions['regime'].values
    for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL, Regime.NEUTRAL]:
        mask = regimes == regime
        if mask.any():
            ax.fill_between(
                price.index, price.min() * 0.99, price.max() * 1.01,
                where=mask, alpha=0.15, color=REGIME_COLORS[regime],
                label=REGIME_LABELS[regime]
            )

    ax.set_ylabel('Price')
    ax.legend(loc='upper left', fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # --- Panel 2: State probabilities ---
    ax2 = axes[1]
    ax2.stackplot(
        predictions.index,
        predictions['prob_trending'].values,
        predictions['prob_ranging'].values,
        predictions['prob_highvol'].values,
        labels=['Trending', 'Ranging', 'High Vol'],
        colors=[REGIME_COLORS[Regime.TRENDING], REGIME_COLORS[Regime.RANGING],
                REGIME_COLORS[Regime.HIGH_VOL]],
        alpha=0.7,
    )
    ax2.axhline(y=HMM_MIN_CONFIDENCE, color='white', linestyle='--', linewidth=1, alpha=0.7)
    ax2.set_ylabel('Probability')
    ax2.set_ylim(0, 1)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # --- Panel 3: Regime confidence ---
    ax3 = axes[2]
    ax3.fill_between(
        predictions.index, 0, predictions['confidence'].values,
        alpha=0.5, color='#4CAF50'
    )
    ax3.axhline(y=HMM_MIN_CONFIDENCE, color='red', linestyle='--',
                linewidth=1, label=f'Min confidence ({HMM_MIN_CONFIDENCE})')
    ax3.set_ylabel('Confidence')
    ax3.set_ylim(0, 1)
    ax3.set_xlabel('Date')
    ax3.legend(loc='upper left', fontsize=8)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    plt.tight_layout()
    path = os.path.join(LOGS_DIR, f'regime_overlay_{symbol.lower()}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def _plot_regime_stats(
    predictions: pd.DataFrame,
    trans_matrix: pd.DataFrame,
    symbol: str,
):
    """Plot regime distribution + transition matrix."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'{symbol} HMM Regime Statistics', fontsize=14, fontweight='bold')

    # --- Regime distribution ---
    ax = axes[0]
    regime_counts = {}
    for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL, Regime.NEUTRAL]:
        count = (predictions['regime'] == regime).sum()
        if count > 0:
            regime_counts[REGIME_LABELS[regime]] = count

    colors = [REGIME_COLORS[r] for r in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL, Regime.NEUTRAL]
              if REGIME_LABELS[r] in regime_counts]
    ax.bar(regime_counts.keys(), regime_counts.values(), color=colors, alpha=0.8)
    ax.set_title('Regime Distribution (bars)')
    ax.set_ylabel('Count')
    for i, (name, count) in enumerate(regime_counts.items()):
        pct = count / len(predictions) * 100
        ax.text(i, count + 50, f'{pct:.1f}%', ha='center', fontweight='bold')

    # --- Transition matrix heatmap ---
    ax2 = axes[1]
    im = ax2.imshow(trans_matrix.values, cmap='YlOrRd', vmin=0, vmax=1)
    ax2.set_xticks(range(3))
    ax2.set_yticks(range(3))
    ax2.set_xticklabels(trans_matrix.columns, fontsize=9)
    ax2.set_yticklabels(trans_matrix.index, fontsize=9)
    ax2.set_title('Transition Probabilities')
    ax2.set_xlabel('To')
    ax2.set_ylabel('From')

    # Annotate cells
    for i in range(3):
        for j in range(3):
            val = trans_matrix.values[i, j]
            color = 'white' if val > 0.5 else 'black'
            ax2.text(j, i, f'{val:.2f}', ha='center', va='center',
                     color=color, fontweight='bold')

    plt.colorbar(im, ax=ax2, shrink=0.8)
    plt.tight_layout()
    path = os.path.join(LOGS_DIR, f'regime_stats_{symbol.lower()}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def _plot_feature_distributions(
    features: pd.DataFrame,
    predictions: pd.DataFrame,
    symbol: str,
):
    """Plot feature distributions per regime."""
    feature_names = RegimeFeatureEngine.FEATURE_NAMES
    n_features = len(feature_names)

    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    fig.suptitle(f'{symbol} Feature Distributions by Regime', fontsize=14, fontweight='bold')
    axes = axes.flatten()

    for i, fname in enumerate(feature_names):
        ax = axes[i]
        for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL]:
            mask = predictions['regime'] == regime
            if mask.sum() > 0:
                vals = features.loc[mask.values, fname].dropna()
                if len(vals) > 0:
                    ax.hist(vals, bins=50, alpha=0.5, density=True,
                            color=REGIME_COLORS[regime], label=REGIME_LABELS[regime])
        ax.set_title(fname, fontsize=10)
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=8)

    plt.tight_layout()
    path = os.path.join(LOGS_DIR, f'regime_features_{symbol.lower()}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    detector, predictions = train_hmm("EURUSD")
