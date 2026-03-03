import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator

import config.settings_mr as opt_settings
from src.regime.regime_detector import Regime
from src.strategy.core import Signal, Direction

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add Mean Reversion-specific technical indicators to an OHLC DataFrame."""
    out = df.copy()

    # ATR
    atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'],
                               window=opt_settings.ATR_PERIOD, fillna=False)
    out['atr'] = atr_ind.average_true_range()

    # RSI
    rsi_ind = RSIIndicator(close=df['close'], window=opt_settings.MR_RSI_PERIOD, fillna=False)
    out['rsi'] = rsi_ind.rsi()

    # EMAs
    out['ema_fast'] = EMAIndicator(close=df['close'], window=opt_settings.EMA_FAST, fillna=False).ema_indicator()
    out['ema_slow'] = EMAIndicator(close=df['close'], window=opt_settings.EMA_SLOW, fillna=False).ema_indicator()

    # Bollinger Bands
    bb = BollingerBands(close=df['close'], window=opt_settings.MR_BB_PERIOD, window_dev=opt_settings.MR_BB_STD, fillna=False)
    out['bb_upper'] = bb.bollinger_hband()
    out['bb_lower'] = bb.bollinger_lband()
    out['bb_mid'] = bb.bollinger_mavg()

    return out

class MeanReversionStrategy:
    """
    Module 2: Mean Reversion
    Activation: RANGING regime with >70% confidence

    Entry: RSI extreme + BB extreme + confirmation candle
    SL: ATR(14) x 1.2 beyond BB extreme
    TP: BB midline, min 1:1.5 RR
    Time exit: 20 bars
    """

    def __init__(self, symbol: str = "EURUSD"):
        self.symbol = symbol
        self.name = "meanrev"

    def generate_signals(
        self,
        entry_df: pd.DataFrame,
        h1_regime: pd.DataFrame,
        h4_structure: pd.Series,
    ) -> list[Signal]:
        """Scan for mean reversion entries on 15m data."""
        signals = []
        df = compute_indicators(entry_df)

        for i in range(max(opt_settings.MR_BB_PERIOD, opt_settings.MR_RSI_PERIOD) + 5, len(df)):
            bar = df.iloc[i]
            prev = df.iloc[i - 1]
            ts = df.index[i]

            if pd.isna(bar['atr']) or pd.isna(bar['rsi']) or pd.isna(bar['bb_upper']):
                continue

            # --- Regime gate ---
            regime_row = self._get_regime_at(ts, h1_regime)
            if regime_row is None:
                continue
            if regime_row['regime'] != Regime.RANGING:
                continue
            if regime_row['confidence'] < opt_settings.HMM_MIN_CONFIDENCE:
                continue

            # --- EMA proximity check (must be ranging) ---
            if not pd.isna(bar['ema_fast']) and not pd.isna(bar['ema_slow']) and bar['atr'] > 0:
                ema_prox = abs(bar['ema_fast'] - bar['ema_slow']) / bar['atr']
                if ema_prox > opt_settings.EMA_PROXIMITY_THRESHOLD * 10:  # Wide EMAs = not ranging
                    continue

            atr = bar['atr']
            if atr <= 0:
                continue

            # --- LONG: oversold at lower BB ---
            if (bar['rsi'] < opt_settings.MR_RSI_OVERSOLD and
                prev['low'] <= prev['bb_lower'] and  # Previous touched lower BB
                bar['close'] > bar['bb_lower']):      # Confirmation: closed back inside

                entry = bar['close']
                sl = entry - opt_settings.MR_SL_ATR_MULT * atr
                # TP = BB midline, but ensure min RR
                tp_bb = bar['bb_mid']
                tp_min = entry + opt_settings.MR_MIN_RR * (entry - sl)
                tp = max(tp_bb, tp_min)

                signals.append(Signal(
                    timestamp=ts, symbol=self.symbol,
                    direction=Direction.LONG, module=self.name,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    atr_at_entry=atr, regime=Regime.RANGING,
                    regime_confidence=regime_row['confidence'],
                    risk_pct=opt_settings.BASE_RISK_PCT
                ))

            # --- SHORT: overbought at upper BB ---
            elif (bar['rsi'] > opt_settings.MR_RSI_OVERBOUGHT and
                  prev['high'] >= prev['bb_upper'] and  # Previous touched upper BB
                  bar['close'] < bar['bb_upper']):       # Confirmation

                entry = bar['close']
                sl = entry + opt_settings.MR_SL_ATR_MULT * atr
                tp_bb = bar['bb_mid']
                tp_min = entry - opt_settings.MR_MIN_RR * (sl - entry)
                tp = min(tp_bb, tp_min)

                signals.append(Signal(
                    timestamp=ts, symbol=self.symbol,
                    direction=Direction.SHORT, module=self.name,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    atr_at_entry=atr, regime=Regime.RANGING,
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
