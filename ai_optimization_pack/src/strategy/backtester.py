"""
AMR-QTS Backtester Engine

Simulates trades from strategy signals with realistic execution:
  - Spread + slippage modeling
  - SL/TP/trailing stop/time exit/regime change exits
  - MFE/MAE tracking
  - Per-trade logging
"""

import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    SPREAD_PIPS, MAX_SLIPPAGE_PIPS,
    TREND_RR_TRAIL_ACTIVATION, TREND_MFE_RETRACE_EXIT,
    MR_TIME_EXIT_BARS, ATR_PERIOD,
)
from src.strategy.modules import Signal, Trade, Direction
from src.regime.regime_detector import Regime


class Backtester:
    """
    Event-driven backtester.
    Walks through 15m bars and manages open positions from signals.
    """

    def __init__(
        self,
        spread_pips: float = 0.0,
        slippage_max: float = 0.0,
        use_trailing: bool = True,
        check_regime_exit: bool = True,
    ):
        self.spread_pips = spread_pips
        self.slippage_max = slippage_max
        self.use_trailing = use_trailing
        self.check_regime_exit = check_regime_exit

    def simulate_trades(
        self,
        signals: list[Signal],
        price_data: pd.DataFrame,  # 15m OHLC for trade management
        h1_regime: pd.DataFrame = None,  # For regime change exits
    ) -> list[Trade]:
        """
        Simulate each signal forward through price bars.
        Returns list of completed Trade objects.
        """
        if not signals:
            return []

        trades = []
        for signal in signals:
            trade = self._simulate_one(signal, price_data, h1_regime)
            if trade is not None:
                trades.append(trade)

        return trades

    def _simulate_one(
        self,
        signal: Signal,
        price_data: pd.DataFrame,
        h1_regime: pd.DataFrame = None,
    ) -> Trade | None:
        """Simulate a single trade forward."""
        # Find bars after signal
        future_bars = price_data.loc[price_data.index > signal.timestamp]
        if len(future_bars) == 0:
            return None

        direction = signal.direction
        entry = signal.entry_price

        # Apply spread + slippage to entry
        spread = SPREAD_PIPS.get(signal.symbol, 0.2) / 10000
        slippage = np.random.uniform(0, self.slippage_max) / 10000
        if direction == Direction.LONG:
            entry += spread + slippage
        else:
            entry -= spread + slippage

        sl = signal.stop_loss
        tp = signal.take_profit
        risk_dist = abs(entry - sl)

        # Tracking
        mfe = 0.0
        mae = 0.0
        trailing_sl = sl
        trail_activated = False

        for bar_idx, (ts, bar) in enumerate(future_bars.iterrows()):
            # Update MFE/MAE
            if direction == Direction.LONG:
                favorable = bar['high'] - entry
                adverse = entry - bar['low']
            else:
                favorable = entry - bar['low']
                adverse = bar['high'] - entry

            mfe = max(mfe, favorable)
            mae = max(mae, adverse)

            # --- Check SL hit ---
            if direction == Direction.LONG and bar['low'] <= trailing_sl:
                exit_price = trailing_sl - np.random.uniform(0, 0.5) / 10000
                reason = 'trail' if trail_activated else 'sl'
                return Trade(
                    signal=signal, exit_price=exit_price, exit_time=ts,
                    exit_reason=reason, bars_held=bar_idx + 1,
                    mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                )
            elif direction == Direction.SHORT and bar['high'] >= trailing_sl:
                exit_price = trailing_sl + np.random.uniform(0, 0.5) / 10000
                reason = 'trail' if trail_activated else 'sl'
                return Trade(
                    signal=signal, exit_price=exit_price, exit_time=ts,
                    exit_reason=reason, bars_held=bar_idx + 1,
                    mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                )

            # --- Check TP hit ---
            if direction == Direction.LONG and bar['high'] >= tp:
                exit_price = tp - np.random.uniform(0, 0.2) / 10000
                return Trade(
                    signal=signal, exit_price=exit_price, exit_time=ts,
                    exit_reason='tp', bars_held=bar_idx + 1,
                    mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                )
            elif direction == Direction.SHORT and bar['low'] <= tp:
                exit_price = tp + np.random.uniform(0, 0.2) / 10000
                return Trade(
                    signal=signal, exit_price=exit_price, exit_time=ts,
                    exit_reason='tp', bars_held=bar_idx + 1,
                    mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                )

            # MFE retrace exit disabled — trailing stop handles profit protection
            # (optimization: MFE retrace produced mostly tiny +1 pip wins while
            # preventing the trail from capturing larger moves)

            # --- Trailing stop (trend module) ---
            if self.use_trailing and signal.module == 'trend':
                trail_trigger = entry + direction * TREND_RR_TRAIL_ACTIVATION * risk_dist
                if direction == Direction.LONG and bar['high'] >= trail_trigger:
                    trail_activated = True
                    new_sl = bar['high'] - signal.atr_at_entry
                    trailing_sl = max(trailing_sl, new_sl)
                elif direction == Direction.SHORT and bar['low'] <= trail_trigger:
                    trail_activated = True
                    new_sl = bar['low'] + signal.atr_at_entry
                    trailing_sl = min(trailing_sl, new_sl)

            # --- Time exit (mean reversion module) ---
            if signal.module == 'meanrev' and bar_idx + 1 >= MR_TIME_EXIT_BARS:
                return Trade(
                    signal=signal, exit_price=bar['close'], exit_time=ts,
                    exit_reason='time', bars_held=bar_idx + 1,
                    mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                )

            # --- Regime change exit ---
            if self.check_regime_exit and h1_regime is not None:
                curr_regime = self._current_regime(ts, h1_regime)
                if curr_regime is not None and curr_regime != signal.regime:
                    # Module-specific regime change behavior
                    if signal.module == 'meanrev' and curr_regime == Regime.TRENDING:
                        # "RANGE -> TREND: Exit mean reversion immediately"
                        return Trade(
                            signal=signal, exit_price=bar['close'], exit_time=ts,
                            exit_reason='regime_change', bars_held=bar_idx + 1,
                            mfe_pips=mfe * 10000, mae_pips=mae * 10000,
                        )

        # If we reach end of data, close at last bar
        last_bar = future_bars.iloc[-1]
        return Trade(
            signal=signal, exit_price=last_bar['close'],
            exit_time=future_bars.index[-1],
            exit_reason='eod', bars_held=len(future_bars),
            mfe_pips=mfe * 10000, mae_pips=mae * 10000,
        )

    def _current_regime(self, ts, h1_regime):
        """Get regime at given timestamp."""
        valid = h1_regime.index[h1_regime.index <= ts]
        if len(valid) == 0:
            return None
        return h1_regime.loc[valid[-1], 'regime']


def analyze_trades(trades: list[Trade], module_name: str = "") -> dict:
    """
    Compute performance metrics from a list of trades.
    Returns dict of metrics.
    """
    if not trades:
        return {'n_trades': 0}

    pnls = [t.pnl_pips for t in trades]
    pnl_r = [t.pnl_r for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    win_rate = len(wins) / len(pnls) if pnls else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float('inf')
    expectancy = np.mean(pnls)

    # Drawdown
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

    # Sharpe (annualized, assuming ~250 trading days, ~6 trades/day for 15m)
    if len(pnl_r) > 1 and np.std(pnl_r) > 0:
        sharpe = np.mean(pnl_r) / np.std(pnl_r) * np.sqrt(252)
    else:
        sharpe = 0

    # Exit reasons
    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    # Average bars held
    avg_bars = np.mean([t.bars_held for t in trades])

    # MFE/MAE
    avg_mfe = np.mean([t.mfe_pips for t in trades])
    avg_mae = np.mean([t.mae_pips for t in trades])

    return {
        'module': module_name,
        'n_trades': len(trades),
        'total_pnl_pips': total_pnl,
        'win_rate': win_rate,
        'avg_win_pips': avg_win,
        'avg_loss_pips': avg_loss,
        'profit_factor': profit_factor,
        'expectancy_pips': expectancy,
        'sharpe': sharpe,
        'max_dd_pips': max_dd,
        'avg_bars_held': avg_bars,
        'avg_rr': avg_win / avg_loss if avg_loss > 0 else 0,
        'avg_mfe_pips': avg_mfe,
        'avg_mae_pips': avg_mae,
        'exit_reasons': exit_reasons,
    }


def print_metrics(metrics: dict):
    """Pretty-print performance metrics."""
    if metrics['n_trades'] == 0:
        print(f"  {metrics.get('module', '???')}: NO TRADES")
        return

    m = metrics
    print(f"\n  {m['module'].upper()} PERFORMANCE")
    print(f"  {'=' * 45}")
    print(f"  Trades:         {m['n_trades']:>8}")
    print(f"  Win Rate:       {m['win_rate']:>8.1%}")
    print(f"  Profit Factor:  {m['profit_factor']:>8.2f}")
    print(f"  Sharpe Ratio:   {m['sharpe']:>8.2f}")
    print(f"  Total PnL:      {m['total_pnl_pips']:>+8.1f} pips")
    print(f"  Expectancy:     {m['expectancy_pips']:>+8.2f} pips/trade")
    print(f"  Avg Win:        {m['avg_win_pips']:>+8.1f} pips")
    print(f"  Avg Loss:       {m['avg_loss_pips']:>8.1f} pips")
    print(f"  Avg R:R:        {m['avg_rr']:>8.2f}")
    print(f"  Max Drawdown:   {m['max_dd_pips']:>8.1f} pips")
    print(f"  Avg Bars Held:  {m['avg_bars_held']:>8.1f}")
    print(f"  Avg MFE:        {m['avg_mfe_pips']:>8.1f} pips")
    print(f"  Avg MAE:        {m['avg_mae_pips']:>8.1f} pips")
    print(f"  Exit Reasons:   {m['exit_reasons']}")
