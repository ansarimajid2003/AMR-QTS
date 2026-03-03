# AMR-QTS — Pre-Development Checklist

> **All times in UTC across the entire system.** No local time conversions anywhere — MT5, Python, logs, session filters, news filters, all UTC.

---

## GLOBAL SETUP (Before Any Phase)

### Python Environment
- [ ] Python 3.10+ installed
- [ ] Virtual environment created: `python -m venv amr-qts-env`
- [ ] IDE: VS Code (free) or PyCharm Community (free)

### Core Libraries
```bash
pip install numpy pandas scipy matplotlib seaborn
pip install MetaTrader5        # MT5 Python bridge (free, Windows only)
pip install hmmlearn            # Hidden Markov Models (free)
pip install ta                  # Technical indicators (free, no C dependencies)
pip install yfinance            # VIX + US10Y data (free Yahoo Finance API)
pip install joblib              # Model serialization (built-in)
pip install python-telegram-bot # Alert system (free)
pip install scikit-learn        # ML utilities, preprocessing (free)
```

### Optional Libraries
```bash
pip install mlfinlab          # CPCV implementation (open source — verify license)
pip install statsmodels       # Structural break tests (free)
pip install plotly             # Interactive charts (free)
```

### MT5 Setup
- [ ] MetaTrader 5 installed (free from broker)
- [ ] Broker account opened (demo is fine for Phases 1–4)
- [ ] Broker must provide: EURUSD, GBPUSD, USDJPY, GBPJPY, XAUUSD, DXY/USDX
- [ ] MT5 terminal set to **UTC timezone** (Tools → Options → Server → uncheck DST)
- [ ] Algo trading enabled (Tools → Options → Expert Advisors → Allow)
- [ ] MQL5 editor available (built into MT5, free)

### Telegram Bot (Alerts)
- [ ] Create bot via @BotFather on Telegram (free)
- [ ] Save bot token + chat ID
- [ ] Test `send_message` works

### Version Control
- [ ] Git installed
- [ ] Repository initialized for the project

---

## PHASE 1 — Research & Backtesting in Python

### Data Required

| Data | Timeframes | Min Length | Source | Cost |
|---|---|---|---|---|
| EURUSD OHLCV | 5m, 15m, H1, H4, Daily | 3 years | MT5 Python API `copy_rates_range()` | Free |
| GBPUSD OHLCV | 5m, 15m, H1, H4, Daily | 3 years | MT5 Python API | Free |
| USDJPY OHLCV | 15m, H1, H4, Daily | 3 years | MT5 Python API (optional Phase 1) | Free |
| DXY (USDX) | H1, Daily | 3 years | MT5 symbol `USDX` or yfinance `DX-Y.NYB` | Free |
| VIX | Daily | 3 years | yfinance `^VIX` | Free |
| US 10Y Yield | Daily | 3 years | yfinance `^TNX` or FRED API (`DGS10`) | Free |

### Data Cleaning Checklist
- [ ] Remove zero-volume bars
- [ ] Remove bank holiday gaps (Dec 25, Jan 1, etc.)
- [ ] Remove Sunday open bars with spread > 5× normal
- [ ] Verify all timestamps are **UTC**
- [ ] Add spread column: EURUSD 0.2 pips, GBPUSD 0.4 pips, USDJPY 0.3 pips
- [ ] Add slippage model: random 0–0.3 pips per trade

### Testing Environment
- [ ] Jupyter Notebook or `.py` scripts — no MT5 backtester
- [ ] Each module tested in isolation first
- [ ] Edge validation tests (random entry benchmark, signal decay, PnL attribution)
- [ ] HMM trained and evaluated vs rule-based detector

### Phase 1 Deliverables
- [ ] Clean dataset (CSV or Parquet)
- [ ] HMM trained model (`hmm_model.pkl`)
- [ ] Per-module backtest results table
- [ ] Edge validation report
- [ ] HMM vs rules comparison table

---

## PHASE 2 — Combined System + Validation

### Additional Libraries (if not already installed)
```bash
pip install mlfinlab    # For CPCV — or implement manually (~50 lines)
```

### Tests Required

| Test | Tool | Pass Criteria |
|---|---|---|
| Walk-Forward | Custom Python | ≥ 70% forward windows profitable |
| Monte Carlo (1,000 runs) | Custom Python (`numpy.random`) | 95th percentile DD < 20% |
| Spread +50% stress test | Custom Python | System still profitable |
| Param ±20% sensitivity | Custom Python | No catastrophic failure |
| Remove best 20 trades | Custom Python | Still profitable |
| CPCV | `mlfinlab` or custom | Median fold Sharpe > 0.5 |
| Deflated Sharpe Ratio | `scipy.stats` (~20 lines) | DSR > 0.95 |
| Min Backtest Length | Formula (scipy) | MinBTL < 3 years (data is sufficient) |
| Regime-conditional Sharpe | Custom Python | Positive Sharpe per regime |

### Phase 2 Deliverables
- [ ] Combined system equity curve
- [ ] Walk-forward results table
- [ ] Monte Carlo DD distribution plot
- [ ] Robustness test pass/fail summary
- [ ] DSR calculation result
- [ ] Decision: HMM primary or rules primary?

---

## PHASE 3 — MT5 EA Development

### Development Environment
- [ ] MetaEditor (built into MT5, free)
- [ ] MQL5 compiler (built into MetaEditor)
- [ ] MT5 Strategy Tester for basic sanity checks (not primary backtest)

### EA File Structure
```
AMR-QTS/
├── MainEA.mq5
├── include/
│   ├── RegimeDetector.mqh
│   ├── TrendModule.mqh
│   ├── MeanReversionModule.mqh
│   ├── HighVolModule.mqh
│   ├── RiskManager.mqh
│   ├── EquityCurveControl.mqh
│   ├── NewsFilter.mqh
│   ├── TransitionManager.mqh
│   └── ExecutionManager.mqh
├── python/
│   ├── hmm_model.pkl
│   ├── regime_server.py
│   └── monitor.py
└── logs/
    └── trades_log.csv
```

### Python ↔ MT5 Bridge
- [ ] File bridge: Python writes `regime_signal.csv` → EA reads it
- [ ] Schedule: Python script runs on H1 bar close via Windows Task Scheduler (free) or `schedule` lib
- [ ] Fallback: if file not updated in 2 hours, EA uses rule-based detector

### Phase 3 Deliverables
- [ ] Compiling EA with all modules
- [ ] All input toggles functional
- [ ] CSV trade logging verified
- [ ] Telegram alerts working
- [ ] Python bridge tested (write → read → correct regime)

---

## PHASE 4 — Demo Forward Test (3 Months)

### Environment
- [ ] MT5 demo account (free from broker)
- [ ] EA attached to: EURUSD 15m chart, GBPUSD 15m chart
- [ ] Python `monitor.py` running daily (Windows Task Scheduler or manual)
- [ ] VPS optional — free tier from Oracle Cloud or AWS (12-month free)

### Monitoring Checklist (Weekly)

| Check | Tool | Target |
|---|---|---|
| Equity curve slope | `monitor.py` or manual CSV review | Positive |
| Max daily DD | Trade log CSV | < 3% |
| Max overall DD | Trade log CSV | < 8% |
| Monthly return | Trade log CSV | 2–7% |
| Realized vs backtested Sharpe | `monitor.py` | Within 1σ |
| HMM vs rules prediction accuracy | Parallel log comparison | Track |
| Avg fill slippage | Trade log CSV | < 0.3 pips EURUSD |

### Rules
- [ ] Zero parameter changes for 3 months
- [ ] Zero manual trades
- [ ] All regime changes logged

### Phase 4 Deliverables
- [ ] 3-month equity curve
- [ ] Performance summary table
- [ ] HMM accuracy report
- [ ] Slippage analysis
- [ ] Go / No-Go decision for Phase 5

---

## PHASE 5 — Prop Firm Deployment

### Requirements
- [ ] Prop firm selected (FTMO, MyFundedFX, etc.) — confirm exact rules
- [ ] Exact daily DD limit noted (e.g., 5%) → system cap remains at 3%
- [ ] Exact overall DD limit noted (e.g., 10%) → system cap remains at 8%
- [ ] Challenge duration noted → align with Phase 5 timeline
- [ ] Risk reduced to **0.3%** for challenge phase
- [ ] Live VPS recommended — Oracle Cloud free tier or similar

### Session Filters (All UTC)

| Rule | Time (UTC) |
|---|---|
| London Open trading starts | 07:00 |
| NY Overlap window | 12:00–16:00 |
| Asian session (USDJPY only) | 00:00–07:00 |
| Friday cutoff | 18:00 — no new trades |
| Sunday no-trade window | Before 22:00 |
| No entries before session close | Last 60 min |

---

## UTC STANDARDIZATION NOTE

> [!IMPORTANT]
> Every component uses UTC. No exceptions.

| Component | How to Set |
|---|---|
| MT5 Terminal | Tools → Options → Server → UTC, uncheck DST |
| Python `datetime` | Always use `datetime.utcnow()` or `datetime.now(timezone.utc)` |
| Trade log CSV | Timestamp column = UTC |
| HMM features | All computed on UTC-aligned bars |
| Session filter | Hardcoded UTC times (table above) |
| News filter | Event times from calendar in UTC |
| Telegram alerts | Display UTC in message body |
| Cron / Task Scheduler | Set to UTC if possible, else offset manually |

---

## FULL COST SUMMARY

| Item | Cost |
|---|---|
| Python + all libraries | Free |
| MT5 + demo account | Free |
| MetaEditor (MQL5 IDE) | Free |
| yfinance (VIX, yields) | Free |
| FRED API (optional) | Free |
| Telegram bot | Free |
| Git version control | Free |
| VPS (optional Phase 4+) | Free tier (Oracle/AWS) |
| **Total** | **$0** |

---

*Checklist Version: 1.0 | System Plan: v3.0 | 2026-02-27*
