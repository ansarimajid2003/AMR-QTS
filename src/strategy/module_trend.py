import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

import config.settings_trend as opt_settings
from src.regime.regime_detector import Regime
from src.strategy.core import Signal, Direction

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add Trend-specific technical indicators to an OHLC DataFrame."""
    out = df.copy()

    # ATR
    atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'],
                               window=opt_settings.ATR_PERIOD, fillna=False)
    out['atr'] = atr_ind.average_true_range()

    # RSI (Trend Specific 14-period)
    rsi_ind = RSIIndicator(close=df['close'], window=opt_settings.TREND_RSI_PERIOD, fillna=False)
    out['rsi'] = rsi_ind.rsi()

    # EMA
    out['ema_slow'] = EMAIndicator(close=df['close'], window=opt_settings.EMA_SLOW, fillna=False).ema_indicator()

    # Bar range
    out['bar_range'] = df['high'] - df['low']

    # Rolling highs/lows for breakout
    out['high_20'] = df['high'].rolling(opt_settings.TREND_BREAKOUT_BARS).max().shift(1)
    out['low_20'] = df['low'].rolling(opt_settings.TREND_BREAKOUT_BARS).min().shift(1)

    # Average bar range for expansion checks
    out['avg_range_5'] = out['bar_range'].rolling(5).mean().shift(1)

    return out


class TrendStrategy:
    """
    Module 1: Trend Continuation
    Activation: TRENDING regime with >70% confidence

    Entry: 20-bar breakout + ATR expansion + RSI filter
    SL: ATR(14) x 1.5
    TP: 1:2 RR, trailing at 1:1
    """

    def __init__(self, symbol: str = "EURUSD"):
        self.symbol = symbol
        self.name = "trend"

    def generate_signals(
        self,
        entry_df: pd.DataFrame,    # 15m data with indicators
        h1_regime: pd.DataFrame,  # Regime predictions (regime, confidence)
        h4_structure: pd.Series,  # H4 structural trend (1/-1/0)
    ) -> list[Signal]:
        """Scan for trend continuation entries on 15m data."""
        signals = []
        df = compute_indicators(entry_df)

        for i in range(opt_settings.TREND_BREAKOUT_BARS + 5, len(df)):
            bar = df.iloc[i]
            ts = df.index[i]

            # Skip if indicators not ready
            if pd.isna(bar['atr']) or pd.isna(bar['rsi']) or pd.isna(bar['ema_slow']):
                continue

            # --- Regime gate ---
            regime_row = self._get_regime_at(ts, h1_regime)
            if regime_row is None:
                continue
            if regime_row['regime'] != Regime.TRENDING:
                continue
            if regime_row['confidence'] < opt_settings.HMM_MIN_CONFIDENCE:
                continue

            # --- H4 structure confirmation ---
            h4_dir = self._get_h4_at(ts, h4_structure)

            atr = bar['atr']
            if atr <= 0:
                continue

            # --- LONG setup ---
            if (h4_dir >= 0 and  # H4 not downtrending
                bar['close'] > bar['high_20'] and  # 20-bar breakout
                (bar['close'] > bar['ema_slow'] if opt_settings.TREND_USE_EMA_FILTER else True) and  # Optional EMA200
                bar['bar_range'] > opt_settings.TREND_ATR_EXPANSION * bar['avg_range_5'] and  # ATR expansion
                opt_settings.TREND_RSI_LONG_MIN <= bar['rsi'] <= opt_settings.TREND_RSI_LONG_MAX):  # Dynamic RSI filter

                entry = bar['close']
                sl = entry - opt_settings.TREND_SL_ATR_MULT * atr
                tp = entry + opt_settings.TREND_RR_PRIMARY * (entry - sl)

                signals.append(Signal(
                    timestamp=ts, symbol=self.symbol,
                    direction=Direction.LONG, module=self.name,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    atr_at_entry=atr, regime=Regime.TRENDING,
                    regime_confidence=regime_row['confidence'],
                    risk_pct=opt_settings.BASE_RISK_PCT
                ))

            # --- SHORT setup ---
            elif (h4_dir <= 0 and  # H4 not uptrending
                  bar['close'] < bar['low_20'] and  # 20-bar breakdown
                  (bar['close'] < bar['ema_slow'] if opt_settings.TREND_USE_EMA_FILTER else True) and  # Optional EMA200
                  bar['bar_range'] > opt_settings.TREND_ATR_EXPANSION * bar['avg_range_5'] and
                  opt_settings.TREND_RSI_SHORT_MIN <= bar['rsi'] <= opt_settings.TREND_RSI_SHORT_MAX):

                entry = bar['close']
                sl = entry + opt_settings.TREND_SL_ATR_MULT * atr
                tp = entry - opt_settings.TREND_RR_PRIMARY * (sl - entry)

                signals.append(Signal(
                    timestamp=ts, symbol=self.symbol,
                    direction=Direction.SHORT, module=self.name,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    atr_at_entry=atr, regime=Regime.TRENDING,
                    regime_confidence=regime_row['confidence'],
                    risk_pct=opt_settings.BASE_RISK_PCT
                ))

        return signals

    def _get_regime_at(self, ts, h1_regime):
        """Get the latest fully closed H1 regime prior to the completion of the 15m bar."""
        cutoff = ts - pd.Timedelta(minutes=45)
        valid = h1_regime.index[h1_regime.index <= cutoff]
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
