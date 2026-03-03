import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange

import config.settings_hv as opt_settings
from src.regime.regime_detector import Regime
from src.strategy.core import Signal, Direction

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add High Volatility-specific technical indicators to an OHLC DataFrame."""
    out = df.copy()

    # ATR
    atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'],
                               window=opt_settings.ATR_PERIOD, fillna=False)
    out['atr'] = atr_ind.average_true_range()

    # Bar range
    out['bar_range'] = df['high'] - df['low']
    out['body'] = abs(df['close'] - df['open'])
    out['body_ratio'] = out['body'] / out['bar_range'].replace(0, np.nan)

    out['high_20'] = df['high'].rolling(opt_settings.TREND_BREAKOUT_BARS).max().shift(1)

    # Average bar range for expansion checks
    out['avg_range_20'] = out['bar_range'].rolling(20).mean().shift(1)

    # ATR change (3-bar smoothed for HighVol module)
    out['atr_change_pct'] = (out['atr'] - out['atr'].shift(3)) / out['atr'].shift(3)

    return out

class HighVolStrategy:
    """
    Module 3: High Volatility Protocol
    Activation: HIGH_VOL regime with >70% confidence

    Entry: 20-bar breakout + 2x bar range + body ratio + ATR expansion
    SL: ATR(14) x 2.0
    TP: 1:1.5 RR minimum
    Risk: 50% of base (0.25%)
    """

    def __init__(self, symbol: str = "EURUSD"):
        self.symbol = symbol
        self.name = "highvol"

    def generate_signals(
        self,
        entry_df: pd.DataFrame,
        h1_regime: pd.DataFrame,
        h4_structure: pd.Series,
    ) -> list[Signal]:
        """Scan for high volatility entries on 15m data."""
        signals = []
        df = compute_indicators(entry_df)

        for i in range(opt_settings.TREND_BREAKOUT_BARS + 5, len(df)):
            bar = df.iloc[i]
            ts = df.index[i]

            if pd.isna(bar['atr']) or pd.isna(bar['avg_range_20']):
                continue

            # --- Regime gate ---
            regime_row = self._get_regime_at(ts, h1_regime)
            if regime_row is None:
                continue
            if regime_row['regime'] != Regime.HIGH_VOL:
                continue
            if regime_row['confidence'] < opt_settings.HMM_MIN_CONFIDENCE:
                continue

            atr = bar['atr']
            if atr <= 0:
                continue

            # Volatility expansion checks
            range_expansion = bar['bar_range'] > opt_settings.HV_BAR_RANGE_MULT * bar['avg_range_20']
            body_ok = bar['body_ratio'] > opt_settings.HV_BODY_RATIO if not pd.isna(bar['body_ratio']) else False
            atr_expanding = bar['atr_change_pct'] > opt_settings.HV_ATR_EXPANSION if not pd.isna(bar['atr_change_pct']) else False

            if not (range_expansion and body_ok and atr_expanding):
                continue

            # Risk is reduced by 50%
            risk = opt_settings.BASE_RISK_PCT * opt_settings.HV_RISK_REDUCTION

            # --- H4 directional filter ---
            h4_dir = self._get_h4_at(ts, h4_structure)

            # --- LONG: breakout above 20-bar high + H4 not downtrending ---
            if (bar['close'] > bar['high_20'] and bar['close'] > bar['open']
                    and h4_dir >= 0):
                entry = bar['close']
                sl = entry - opt_settings.HV_SL_ATR_MULT * atr
                tp = entry + opt_settings.HV_MIN_RR * (entry - sl)

                signals.append(Signal(
                    timestamp=ts, symbol=self.symbol,
                    direction=Direction.LONG, module=self.name,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    risk_pct=risk, atr_at_entry=atr,
                    regime=Regime.HIGH_VOL,
                    regime_confidence=regime_row['confidence'],
                ))

            # SHORT entries disabled — optimization analysis showed HighVol shorts
            # lose in all conditions (23% WR, -208 pips) including with H4 filter.
            # Volatility breakdowns reverse too quickly for the 2×ATR stop.

        return signals

    def _get_regime_at(self, ts, h1_regime):
        valid = h1_regime.index[h1_regime.index <= ts]
        if len(valid) == 0:
            return None
        return h1_regime.loc[valid[-1]]

    def _get_h4_at(self, ts, h4_structure):
        """Get the latest fully closed H4 structure prior to the completion of the 15m bar."""
        cutoff = ts - pd.Timedelta(hours=3, minutes=45)
        valid = h4_structure.index[h4_structure.index <= cutoff]
        if len(valid) == 0:
            return 0
        return h4_structure.loc[valid[-1]]
