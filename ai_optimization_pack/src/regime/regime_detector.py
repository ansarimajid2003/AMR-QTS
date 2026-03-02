"""
AMR-QTS Regime Detector — Layer B
Hidden Markov Model (HMM) regime classification with rule-based fallback.

Classifies market state into 3 regimes:
  State 0: TRENDING   → Module 1 (Trend Continuation)
  State 1: RANGING    → Module 2 (Mean Reversion)
  State 2: HIGH_VOL   → Module 3 (High Volatility)

Observable features (computed on H1 data):
  1. log_returns     — log(close / prev_close)
  2. realized_vol    — rolling 20-bar std of returns
  3. adx             — ADX(14), scaled 0-1
  4. adx_slope       — ADX[0] - ADX[3]
  5. atr_ratio       — ATR(14) / 30-bar SMA of ATR(14)
  6. ema_proximity   — abs(EMA50 - EMA200) / ATR(14)
  7. dxy_roc         — 20-bar rate of change of DXY
  8. vix_level       — VIX close, z-scored
"""

import sys
from pathlib import Path
from enum import IntEnum
from dataclasses import dataclass

import numpy as np
import pandas as pd
import joblib
from hmmlearn.hmm import GaussianHMM
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import (
    ADX_PERIOD, ADX_TREND_THRESHOLD, ADX_RANGE_THRESHOLD,
    ADX_SLOPE_BARS, ATR_PERIOD, ATR_HIGH_VOL_RATIO, ATR_30D_WINDOW,
    EMA_FAST, EMA_SLOW, EMA_PROXIMITY_THRESHOLD,
    HMM_N_STATES, HMM_MIN_CONFIDENCE, HMM_TRANSITION_BARS,
)


# ============================================================
# REGIME ENUM
# ============================================================

class Regime(IntEnum):
    TRENDING = 0
    RANGING = 1
    HIGH_VOL = 2
    NEUTRAL = 3  # When no state has >70% confidence


@dataclass
class RegimeResult:
    """Result of a regime prediction for a single bar."""
    regime: Regime
    confidence: float  # Probability of the active regime
    probabilities: np.ndarray  # [P(trending), P(ranging), P(high_vol)]
    raw_state: int  # HMM raw state index before label mapping


# ============================================================
# FEATURE ENGINEERING
# ============================================================

class RegimeFeatureEngine:
    """
    Compute 8 observable features for HMM from H1 OHLCV + cross-asset data.
    All features are z-score normalized using training-set statistics.
    """

    FEATURE_NAMES = [
        'log_returns', 'realized_vol', 'adx', 'adx_slope',
        'atr_ratio', 'ema_proximity', 'dxy_roc', 'vix_level'
    ]

    def __init__(self):
        self.feature_means_ = None
        self.feature_stds_ = None
        self._is_fitted = False

    def compute_raw_features(
        self,
        h1_df: pd.DataFrame,
        dxy_daily: pd.DataFrame = None,
        vix_daily: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """
        Compute raw (unnormalized) features from H1 OHLCV + cross-asset.

        Parameters:
            h1_df: H1 OHLCV DataFrame with DatetimeIndex (UTC).
                   Must have: open, high, low, close
            dxy_daily: DXY daily close (DatetimeIndex, 'close' column)
            vix_daily: VIX daily close (DatetimeIndex, 'close' column)

        Returns:
            DataFrame with 8 feature columns, NaN rows dropped.
        """
        df = h1_df[['open', 'high', 'low', 'close']].copy()

        # 1. Log returns
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # 2. Realized volatility (20-bar rolling std of returns)
        df['realized_vol'] = df['log_returns'].rolling(20).std()

        # 3. ADX(14) — directional movement index, scaled to 0-1
        adx_ind = ADXIndicator(
            high=df['high'], low=df['low'], close=df['close'],
            window=ADX_PERIOD, fillna=False
        )
        df['adx'] = adx_ind.adx() / 100.0  # Scale 0-1

        # 4. ADX slope (current - N bars ago)
        df['adx_slope'] = df['adx'] - df['adx'].shift(ADX_SLOPE_BARS)

        # 5. ATR ratio: ATR(14) / 30-bar SMA of ATR(14)
        atr_ind = AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'],
            window=ATR_PERIOD, fillna=False
        )
        atr = atr_ind.average_true_range()
        atr_sma = atr.rolling(ATR_30D_WINDOW).mean()
        df['atr_ratio'] = atr / atr_sma

        # 6. EMA proximity: abs(EMA50 - EMA200) / ATR(14)
        ema_fast = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
        ema_slow = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
        df['ema_proximity'] = np.abs(ema_fast - ema_slow) / atr

        # 7. DXY rate of change (20-bar)
        if dxy_daily is not None and not dxy_daily.empty:
            dxy = dxy_daily[['close']].rename(columns={'close': 'dxy_close'})
            # Remove timezone if needed for reindex
            dxy_roc = dxy['dxy_close'].pct_change(20)
            # Forward-fill daily DXY to H1 index
            dxy_roc_h1 = dxy_roc.reindex(df.index, method='ffill')
            df['dxy_roc'] = dxy_roc_h1
        else:
            df['dxy_roc'] = 0.0

        # 8. VIX level (z-scored within this function, raw here)
        if vix_daily is not None and not vix_daily.empty:
            vix = vix_daily[['close']].rename(columns={'close': 'vix_close'})
            vix_h1 = vix['vix_close'].reindex(df.index, method='ffill')
            df['vix_level'] = vix_h1
        else:
            df['vix_level'] = 0.0

        # Keep only feature columns
        features = df[self.FEATURE_NAMES].copy()

        # Drop NaN rows (from rolling calculations)
        features.dropna(inplace=True)

        return features

    def fit_normalize(self, features: pd.DataFrame) -> pd.DataFrame:
        """Fit normalization statistics on training data and transform."""
        self.feature_means_ = features.mean()
        self.feature_stds_ = features.std().replace(0, 1)  # Avoid div by 0
        self._is_fitted = True
        return (features - self.feature_means_) / self.feature_stds_

    def normalize(self, features: pd.DataFrame) -> pd.DataFrame:
        """Transform using previously fitted statistics."""
        if not self._is_fitted:
            raise RuntimeError("Call fit_normalize() first on training data.")
        return (features - self.feature_means_) / self.feature_stds_

    def get_normalization_params(self) -> dict:
        """Get normalization parameters for serialization."""
        return {
            'means': self.feature_means_.to_dict(),
            'stds': self.feature_stds_.to_dict(),
        }

    def set_normalization_params(self, params: dict):
        """Set normalization parameters from deserialization."""
        self.feature_means_ = pd.Series(params['means'])
        self.feature_stds_ = pd.Series(params['stds'])
        self._is_fitted = True


# ============================================================
# HMM REGIME DETECTOR
# ============================================================

class HMMRegimeDetector:
    """
    Hidden Markov Model regime detector using hmmlearn.GaussianHMM.

    After training, states are auto-labeled:
      - Highest return variance → HIGH_VOL
      - Highest mean |return| (of remaining) → TRENDING
      - Lowest mean |return| → RANGING
    """

    def __init__(
        self,
        n_states: int = HMM_N_STATES,
        min_confidence: float = HMM_MIN_CONFIDENCE,
        transition_bars: int = HMM_TRANSITION_BARS,
        n_iter: int = 200,
        random_state: int = 42,
    ):
        self.n_states = n_states
        self.min_confidence = min_confidence
        self.transition_bars = transition_bars

        self.hmm = GaussianHMM(
            n_components=n_states,
            covariance_type='full',
            n_iter=n_iter,
            random_state=random_state,
            verbose=False,
        )

        # State label mapping: hmm_state_index → Regime enum
        self.state_map_ = None
        self.feature_engine = RegimeFeatureEngine()
        self._is_fitted = False

    def fit(self, features: pd.DataFrame) -> 'HMMRegimeDetector':
        """
        Train the HMM on normalized feature matrix.

        Parameters:
            features: DataFrame with columns matching FEATURE_NAMES.
                      Should already be z-score normalized.
        """
        X = features.values.astype(np.float64)
        self.hmm.fit(X)
        self._label_states(features)
        self._is_fitted = True
        return self

    def _label_states(self, features: pd.DataFrame):
        """
        Auto-label HMM states by inspecting emission means.

        Logic:
          1. Get mean of each feature per hidden state
          2. Identify log_returns index (feature 0)
          3. State with highest realized_vol mean → HIGH_VOL
          4. Of remaining, highest abs(log_returns mean) → TRENDING
          5. Remaining → RANGING
        """
        means = self.hmm.means_  # shape: (n_states, n_features)

        # Feature indices
        ret_idx = 0   # log_returns
        vol_idx = 1   # realized_vol

        # Step 1: Highest realized volatility → HIGH_VOL
        vol_means = means[:, vol_idx]
        high_vol_state = int(np.argmax(vol_means))

        # Step 2: Of remaining, highest abs return → TRENDING
        remaining = [s for s in range(self.n_states) if s != high_vol_state]
        abs_ret_means = {s: abs(means[s, ret_idx]) for s in remaining}
        trending_state = max(abs_ret_means, key=abs_ret_means.get)

        # Step 3: Remaining → RANGING
        ranging_state = [s for s in remaining if s != trending_state][0]

        # Map: hmm_internal_state → Regime enum
        self.state_map_ = {
            trending_state: Regime.TRENDING,
            ranging_state: Regime.RANGING,
            high_vol_state: Regime.HIGH_VOL,
        }

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict regime for each bar.

        Returns DataFrame with columns:
          - regime: Regime enum value (after smoothing)
          - confidence: max probability
          - prob_trending, prob_ranging, prob_highvol
          - raw_state: HMM internal state (before label mapping)
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        X = features.values.astype(np.float64)

        # Get state probabilities
        raw_states = self.hmm.predict(X)
        state_probs = self.hmm.predict_proba(X)

        # Map raw states to Regime labels
        mapped_regimes = np.array([self.state_map_[s] for s in raw_states])

        # Map probabilities to Regime order: [TRENDING, RANGING, HIGH_VOL]
        inverse_map = {v: k for k, v in self.state_map_.items()}
        prob_trending = state_probs[:, inverse_map[Regime.TRENDING]]
        prob_ranging = state_probs[:, inverse_map[Regime.RANGING]]
        prob_highvol = state_probs[:, inverse_map[Regime.HIGH_VOL]]

        # Build result DataFrame
        result = pd.DataFrame({
            'regime_raw': mapped_regimes,
            'confidence': np.max(state_probs, axis=1),
            'prob_trending': prob_trending,
            'prob_ranging': prob_ranging,
            'prob_highvol': prob_highvol,
            'raw_state': raw_states,
        }, index=features.index)

        # Apply transition smoothing + confidence filter
        result['regime'] = self._smooth_transitions(result)

        return result

    def _smooth_transitions(self, result: pd.DataFrame) -> np.ndarray:
        """
        Apply transition smoothing:
        1. Require N consecutive bars of >min_confidence before switching
        2. If no state exceeds min_confidence → NEUTRAL

        Returns array of Regime enum values.
        """
        regimes_raw = result['regime_raw'].values
        confidences = result['confidence'].values
        smoothed = np.full(len(regimes_raw), Regime.NEUTRAL, dtype=int)

        current_regime = Regime.NEUTRAL
        consecutive_count = 0
        pending_regime = Regime.NEUTRAL

        for i in range(len(regimes_raw)):
            bar_regime = regimes_raw[i]
            bar_conf = confidences[i]

            # Check confidence threshold
            if bar_conf < self.min_confidence:
                # Low confidence — stay in current or go NEUTRAL
                consecutive_count = 0
                pending_regime = Regime.NEUTRAL
                if current_regime == Regime.NEUTRAL:
                    smoothed[i] = Regime.NEUTRAL
                else:
                    # Stay in current regime during brief uncertainty
                    smoothed[i] = current_regime
                continue

            if bar_regime == current_regime:
                # Same regime, just continue
                smoothed[i] = current_regime
                consecutive_count = 0
                pending_regime = current_regime
            elif bar_regime == pending_regime:
                # Building confirmation for new regime
                consecutive_count += 1
                if consecutive_count >= self.transition_bars:
                    # Confirmed transition
                    current_regime = pending_regime
                    smoothed[i] = current_regime
                    consecutive_count = 0
                else:
                    # Not yet confirmed — stay in current
                    smoothed[i] = current_regime
            else:
                # New potential regime
                pending_regime = bar_regime
                consecutive_count = 1
                if self.transition_bars <= 1:
                    current_regime = pending_regime
                    smoothed[i] = current_regime
                else:
                    smoothed[i] = current_regime

        return smoothed

    def score(self, features: pd.DataFrame) -> float:
        """Log-likelihood of the data under the model."""
        X = features.values.astype(np.float64)
        return self.hmm.score(X)

    def get_transition_matrix(self) -> pd.DataFrame:
        """Get the learned transition probability matrix."""
        if not self._is_fitted:
            raise RuntimeError("Model not fitted.")
        labels = ['TRENDING', 'RANGING', 'HIGH_VOL']
        inverse_map = {v: k for k, v in self.state_map_.items()}
        order = [inverse_map[r] for r in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL]]
        trans = self.hmm.transmat_[np.ix_(order, order)]
        return pd.DataFrame(trans, index=labels, columns=labels)

    def get_state_statistics(self) -> pd.DataFrame:
        """Get mean and std of each feature per state."""
        if not self._is_fitted:
            raise RuntimeError("Model not fitted.")
        names = RegimeFeatureEngine.FEATURE_NAMES
        inverse_map = {v: k for k, v in self.state_map_.items()}
        rows = []
        for regime in [Regime.TRENDING, Regime.RANGING, Regime.HIGH_VOL]:
            s = inverse_map[regime]
            means = self.hmm.means_[s]
            stds = np.sqrt(np.diag(self.hmm.covars_[s]))
            for j, name in enumerate(names):
                rows.append({
                    'regime': regime.name,
                    'feature': name,
                    'mean': means[j],
                    'std': stds[j],
                })
        return pd.DataFrame(rows)

    def save(self, filepath: str):
        """Save trained model to disk."""
        data = {
            'hmm': self.hmm,
            'state_map': self.state_map_,
            'n_states': self.n_states,
            'min_confidence': self.min_confidence,
            'transition_bars': self.transition_bars,
            'feature_engine_params': self.feature_engine.get_normalization_params(),
        }
        joblib.dump(data, filepath)

    @classmethod
    def load(cls, filepath: str) -> 'HMMRegimeDetector':
        """Load trained model from disk."""
        data = joblib.load(filepath)
        detector = cls(
            n_states=data['n_states'],
            min_confidence=data['min_confidence'],
            transition_bars=data['transition_bars'],
        )
        detector.hmm = data['hmm']
        detector.state_map_ = data['state_map']
        detector.feature_engine.set_normalization_params(
            data['feature_engine_params']
        )
        detector._is_fitted = True
        return detector


# ============================================================
# RULE-BASED FALLBACK (V2 DETECTOR)
# ============================================================

class RuleBasedDetector:
    """
    Rule-based regime detector using ADX + ATR thresholds.
    Used as a comparison baseline and live fallback.
    """

    def __init__(
        self,
        adx_trend: float = ADX_TREND_THRESHOLD,
        adx_range: float = ADX_RANGE_THRESHOLD,
        atr_high_vol: float = ATR_HIGH_VOL_RATIO,
    ):
        self.adx_trend = adx_trend
        self.adx_range = adx_range
        self.atr_high_vol = atr_high_vol

    def predict(self, h1_df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict regime using simple threshold rules.

        Rules:
          1. ATR ratio > 1.5 → HIGH_VOL (takes priority)
          2. ADX > 25 → TRENDING
          3. ADX < 20 → RANGING
          4. Otherwise → NEUTRAL

        Returns DataFrame with 'regime' and 'confidence' columns.
        """
        df = h1_df[['open', 'high', 'low', 'close']].copy()

        # ADX
        adx_ind = ADXIndicator(
            high=df['high'], low=df['low'], close=df['close'],
            window=ADX_PERIOD, fillna=False
        )
        adx = adx_ind.adx()

        # ATR ratio
        atr_ind = AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'],
            window=ATR_PERIOD, fillna=False
        )
        atr = atr_ind.average_true_range()
        atr_sma = atr.rolling(ATR_30D_WINDOW).mean()
        atr_ratio = atr / atr_sma

        # Classify
        regimes = np.full(len(df), Regime.NEUTRAL, dtype=int)
        confidences = np.full(len(df), 0.5)

        for i in range(len(df)):
            adx_val = adx.iloc[i]
            atr_val = atr_ratio.iloc[i]

            if pd.isna(adx_val) or pd.isna(atr_val):
                continue

            # Priority: HIGH_VOL > TRENDING > RANGING
            if atr_val > self.atr_high_vol:
                regimes[i] = Regime.HIGH_VOL
                confidences[i] = min(atr_val / self.atr_high_vol, 1.0)
            elif adx_val > self.adx_trend:
                regimes[i] = Regime.TRENDING
                confidences[i] = min(adx_val / 50.0, 1.0)
            elif adx_val < self.adx_range:
                regimes[i] = Regime.RANGING
                confidences[i] = min((self.adx_range - adx_val) / self.adx_range + 0.5, 1.0)
            else:
                regimes[i] = Regime.NEUTRAL
                confidences[i] = 0.5

        result = pd.DataFrame({
            'regime': regimes,
            'confidence': confidences,
        }, index=df.index)

        return result
