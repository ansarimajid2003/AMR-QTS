"""
AMR-QTS Backtester Engine - Mean Reversion Module
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config.settings_mr as opt_settings
from src.strategy.core import Signal, Trade, Direction
from src.regime.regime_detector import Regime

class Backtester:
    def __init__(self, spread_pips=0.0, slippage_max=0.0, check_regime_exit=True):
        self.spread_pips = spread_pips
        self.slippage_max = slippage_max
        self.check_regime_exit = check_regime_exit

    def simulate_trades(self, signals: list[Signal], price_data: pd.DataFrame, h1_regime: pd.DataFrame = None) -> list[Trade]:
        if not signals: return []
        trades = []
        for signal in signals:
            trade = self._simulate_one(signal, price_data, h1_regime)
            if trade is not None: trades.append(trade)
        return trades

    def _simulate_one(self, signal: Signal, price_data: pd.DataFrame, h1_regime: pd.DataFrame = None) -> Trade | None:
        future_bars = price_data.loc[price_data.index > signal.timestamp]
        if len(future_bars) == 0: return None

        direction = signal.direction
        entry = signal.entry_price

        if self.spread_pips > 0: spread = self.spread_pips / 10000
        else: spread = opt_settings.SPREAD_PIPS.get(signal.symbol, 0.2) / 10000
        slippage = np.random.uniform(0, self.slippage_max) / 10000
        if direction == Direction.LONG: entry += spread + slippage
        else: entry -= spread + slippage

        sl, tp = signal.stop_loss, signal.take_profit
        mfe, mae = 0.0, 0.0

        for bar_idx, (ts, bar) in enumerate(future_bars.iterrows()):
            favorable = bar['high'] - entry if direction == Direction.LONG else entry - bar['low']
            adverse = entry - bar['low'] if direction == Direction.LONG else bar['high'] - entry
            mfe, mae = max(mfe, favorable), max(mae, adverse)

            # --- Check SL hit ---
            if direction == Direction.LONG and bar['low'] <= sl:
                fill_price = min(bar['open'], sl)
                exit_price = fill_price - np.random.uniform(0, 0.5) / 10000
                return Trade(signal=signal, exit_price=exit_price, exit_time=ts,
                             exit_reason='sl', bars_held=bar_idx + 1,
                             mfe_pips=mfe * 10000, mae_pips=mae * 10000)
            elif direction == Direction.SHORT and bar['high'] >= sl:
                fill_price = max(bar['open'], sl)
                exit_price = fill_price + np.random.uniform(0, 0.5) / 10000
                return Trade(signal=signal, exit_price=exit_price, exit_time=ts,
                             exit_reason='sl', bars_held=bar_idx + 1,
                             mfe_pips=mfe * 10000, mae_pips=mae * 10000)

            # --- Check TP hit ---
            if direction == Direction.LONG and bar['high'] >= tp:
                exit_price = tp - np.random.uniform(0, 0.2) / 10000
                return Trade(signal=signal, exit_price=exit_price, exit_time=ts,
                             exit_reason='tp', bars_held=bar_idx + 1,
                             mfe_pips=mfe * 10000, mae_pips=mae * 10000)
            elif direction == Direction.SHORT and bar['low'] <= tp:
                exit_price = tp + np.random.uniform(0, 0.2) / 10000
                return Trade(signal=signal, exit_price=exit_price, exit_time=ts,
                             exit_reason='tp', bars_held=bar_idx + 1,
                             mfe_pips=mfe * 10000, mae_pips=mae * 10000)

            # --- Time exit ---
            if bar_idx + 1 >= getattr(opt_settings, "MR_TIME_EXIT_BARS", 20):
                return Trade(signal=signal, exit_price=bar['close'], exit_time=ts,
                             exit_reason='time', bars_held=bar_idx + 1,
                             mfe_pips=mfe * 10000, mae_pips=mae * 10000)

            # --- Regime change exit ---
            if self.check_regime_exit and h1_regime is not None:
                curr_regime = self._current_regime(ts, h1_regime)
                if curr_regime is not None and curr_regime != signal.regime:
                    if curr_regime == Regime.TRENDING:
                        return Trade(signal=signal, exit_price=bar['close'], exit_time=ts,
                                     exit_reason='regime_change', bars_held=bar_idx + 1,
                                     mfe_pips=mfe * 10000, mae_pips=mae * 10000)

        last_bar = future_bars.iloc[-1]
        return Trade(signal=signal, exit_price=last_bar['close'], exit_time=future_bars.index[-1],
                     exit_reason='eod', bars_held=len(future_bars),
                     mfe_pips=mfe * 10000, mae_pips=mae * 10000)

    def _current_regime(self, ts, h1_regime):
        cutoff = ts - pd.Timedelta(minutes=45)
        valid = h1_regime.index[h1_regime.index <= cutoff]
        if len(valid) == 0: return None
        return h1_regime.loc[valid[-1], 'regime']

def analyze_trades(trades: list[Trade], module_name: str = "") -> dict:
    if not trades: return {'n_trades': 0}

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

    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

    sharpe = np.mean(pnl_r) / np.std(pnl_r) * np.sqrt(252) if len(pnl_r) > 1 and np.std(pnl_r) > 0 else 0

    exit_reasons = {}
    for t in trades: exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    return {
        'module': module_name, 'n_trades': len(trades), 'total_pnl_pips': total_pnl,
        'win_rate': win_rate, 'avg_win_pips': avg_win, 'avg_loss_pips': avg_loss,
        'profit_factor': profit_factor, 'expectancy_pips': expectancy, 'sharpe': sharpe,
        'max_dd_pips': max_dd, 'avg_bars_held': np.mean([t.bars_held for t in trades]),
        'avg_rr': avg_win / avg_loss if avg_loss > 0 else 0,
        'avg_mfe_pips': np.mean([t.mfe_pips for t in trades]),
        'avg_mae_pips': np.mean([t.mae_pips for t in trades]),
        'exit_reasons': exit_reasons,
    }

def print_metrics(metrics: dict):
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
