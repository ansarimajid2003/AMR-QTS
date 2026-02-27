# PROJECT_CONTEXT.md
> **Context for AI Assistants** — Read this first when switching between tools/IDEs

---

## 🎯 What This File Is For

This document provides **complete context** for AI assistants (Claude, GitHub Copilot, Cursor, etc.) when working on AMR-QTS across multiple sessions or tools. It eliminates the need to re-explain the project architecture, current state, and development philosophy.

**Use this when:**
- Switching between different AI coding assistants
- Starting a new development session
- Onboarding a new AI tool to the project
- Need quick reference for system architecture decisions

---

## 📊 Project Identity

**Name:** AMR-QTS (Adaptive Multi-Regime Quantitative Trading System)  
**Version:** 3.0  
**Type:** Systematic Forex Trading System  
**Target:** Prop firm scaling (personal capital → funded accounts)  
**Current Phase:** Phase 1 — Research & Backtesting  
**Current Task:** Isolating backtest for each strategy module (Module 1, 2, 3)

---

## 🧠 Mental Model — What This System Is

### High-Level Concept
A **regime-adaptive trading system** that switches between 3 strategy modules based on probabilistic market regime classification (HMM). Think of it as:
- **HMM Regime Detector** = Traffic control system
- **3 Strategy Modules** = Different vehicles optimized for different road conditions
- **Risk Management Layer** = Overrides everything, safety first
- **Execution Layer** = Professional order placement (stop/limit, not market spam)

### Not a "Holy Grail" System
- This is NOT trying to predict the future or "beat the market"
- It's exploiting **known behavioral patterns** (momentum persistence, mean reversion in ranges)
- Edge comes from **correct regime classification** + **proper execution timing**
- Survival comes from **portfolio-level risk management**

### Design Philosophy
1. **Alpha-first approach:** Prove the edge exists before building around it
2. **Regime adaptation:** No single strategy works in all market conditions
3. **Risk-first:** Survival > growth (daily caps, correlation controls, volatility filters)
4. **Statistical rigor:** Institutional validation methods (CPCV, Deflated Sharpe, not just "backtest shows profit")
5. **Complexity must earn its place:** Simpler model wins unless complex beats it by ≥10%

---

## 🏗️ Architecture — 5 Layers (Critical to Understand)

### Layer A: Risk Governance (OVERRIDES EVERYTHING)
- This is the **supreme layer** — nothing trades if this layer says no
- Base risk: 0.5% equity per trade
- Daily cap: 3% loss → system disabled for the day
- Max 3 simultaneous trades, total exposure ≤ 2%
- Correlation control, volatility safety switches, news filters
- **Key point:** Position sizing is **portfolio-level**, not per-trade independent

### Layer B: Regime Detection Engine
**Primary Method:** Hidden Markov Model (HMM)
- **Why HMM?** Because markets don't cleanly switch between "trending" and "ranging" with a fixed threshold. HMM gives **probabilities** (e.g., "78% likely in trending state") and learns **transition patterns** from historical data.
- **8 Features:** Returns, realized vol, ADX, ADX slope, ATR ratio, EMA proximity, DXY trend, VIX level
- **3 Hidden States:**
  - State 0: TRENDING LOW VOL → activates Module 1
  - State 1: RANGING LOW VOL → activates Module 2
  - State 2: HIGH VOLATILITY → activates Module 3
- **Decision rule:** Only trade if max(regime_probability) > 0.70. If uncertain (< 0.70), enter NEUTRAL mode (no new entries).
- **Fallback:** Rule-based detector (ADX + ATR thresholds) runs in parallel as backup

**Key Library:** `hmmlearn` (Python)

### Layer C: Strategy Modules (3 Modules)
Each module is a **complete strategy** optimized for a specific regime:

1. **Module 1 — Trend Following**
   - **Edge hypothesis:** Momentum persistence over 1–4 hour windows due to institutional order flow
   - **Entry:** ADX > 25 + EMA crossover + pullback to EMA50
   - **Exit:** Trail ATR × 2.0, fixed TP at 3× risk
   - **Active in:** TRENDING LOW VOL regime

2. **Module 2 — Mean Reversion**
   - **Edge hypothesis:** 2σ deviation from mean in ranges reverts due to market-making behavior
   - **Entry:** Price touches Bollinger Band (2σ), ADX < 25, rejection candle
   - **Exit:** Return to mean (EMA50) or fixed stop at ATR × 1.5
   - **Active in:** RANGING LOW VOL regime

3. **Module 3 — High Volatility**
   - **Edge hypothesis:** Breakouts in high vol environments + rapid reversals
   - **Entry:** H1 range breakout with volume spike, ATR > 1.5× norm
   - **Exit:** Quick profit take (1× ATR) or trail tight (ATR × 1.0)
   - **Active in:** HIGH VOLATILITY regime

**Critical:** Each module is backtested **in isolation first** (current task). Only after proving individual edge do we combine them.

### Layer D: Performance Monitoring
- Real-time Sharpe tracking (5σ deviation = alert)
- Equity curve validation (flatness detection over 30 days)
- Regime misclassification rate monitoring
- Automated daily reports (Telegram alerts)

### Layer E: Execution Layer
- **Stop/limit orders** instead of market orders (reduce slippage)
- **Pending order management:** 4-hour expiry for unfilled orders
- **Slippage tolerance:** Max 1 pip EURUSD, reject fill if exceeded
- **Order book awareness:** Check depth before placing (Phase 3 feature)

---

## 📂 File Structure — Where Everything Lives

```
AMR-QTS/
├── config/
│   └── settings.py              # ALL system parameters (regime thresholds, risk %, etc.)
│
├── data/
│   ├── raw/                     # Downloaded OHLCV (MT5), never modified
│   ├── processed/               # Cleaned, validated, feature-engineered data
│   ├── external/                # DXY, VIX, US10Y from yfinance
│   └── regime_labels/           # HMM output: each bar labeled with regime + probability
│
├── src/
│   ├── data/                    # Data collection & preprocessing
│   ├── regime/                  # HMM detector + fallback rule-based detector
│   ├── strategies/              # 3 strategy modules (trend, mean_reversion, high_vol)
│   ├── backtesting/             # Backtest engine, isolated tests, walk-forward, Monte Carlo
│   ├── risk/                    # Portfolio manager, position sizer, correlation matrix
│   ├── validation/              # Edge tests, CPCV, Deflated Sharpe, robustness checks
│   ├── execution/               # Order manager, slippage model, MT5 bridge
│   └── monitoring/              # Performance tracker, alert system, regime logger
│
├── notebooks/                   # Jupyter notebooks for exploration/analysis
├── tests/                       # Unit + integration tests
├── mt5_ea/                      # Phase 3: MQL5 Expert Advisor files
├── logs/                        # Trade logs, regime changes, performance metrics
├── reports/                     # Backtest results, validation reports, live monitoring
└── docs/                        # System plan, task list, this file
```

**Key principle:** Raw data is immutable. All transformations create new files in `processed/`.

---

## 🔬 Current Development State

### Phase 1 Progress
- ✅ **Setup:** Python 3.12.2 venv, all libraries installed, Git initialized
- ✅ **Data collection:** EURUSD, GBPUSD historical data downloaded (3+ years H1)
- ✅ **Data cleaning:** Validated OHLCV integrity, handled missing bars
- ✅ **HMM regime detector:** Built using `hmmlearn`, trained on 2 years, validated on 1 year
- ✅ **Strategy modules:** All 3 modules implemented as classes with `generate_signals()` method
- 🔄 **Current task:** Isolating backtest for each module (test edge in isolation before combining)

### What "Isolated Backtest" Means
Run each module's signals through the backtest engine **in its preferred regime only**, with:
- No other modules interfering
- Basic risk management (fixed 0.5% risk, ATR-based stops)
- **No optimization** — use default parameters from `config/settings.py`
- Goal: Verify each module has positive expectancy in its target regime

### Next Steps After Current Task
1. **Edge validation tests** (random entry benchmark, signal decay, PnL attribution, top 10% removal)
2. **HMM vs rules comparison** (run both detectors on validation set, compare accuracy)
3. **Combined system backtest** (all 3 modules with HMM regime switching)
4. **Phase 2 validation** (CPCV, Deflated Sharpe, walk-forward, Monte Carlo)

---

## 🛠️ Technical Stack & Key Libraries

### Core Languages
- **Python 3.12.2** — All research, backtesting, regime detection, risk management
- **MQL5** — Phase 3+ (MT5 Expert Advisor, not started yet)

### Critical Python Libraries
```python
# Regime Detection
hmmlearn==0.3.0              # Hidden Markov Model (core of Layer B)

# Data Handling
pandas==2.1.4                # All data manipulation
numpy==1.26.3                # Numerical computing

# Technical Analysis
ta==0.11.0                   # ADX, ATR, Bollinger Bands, EMAs

# External Data
yfinance==0.2.33             # VIX, US10Y data (free)
MetaTrader5==5.0.45          # MT5 API for OHLCV download

# Statistical Validation
scipy==1.11.4                # Deflated Sharpe, statistical tests
statsmodels==0.14.1          # Time series analysis

# Visualization
matplotlib==3.8.2
seaborn==0.13.0
plotly==5.18.0               # Interactive charts

# Model Serialization
joblib==1.3.2                # Save/load trained HMM

# Monitoring
python-telegram-bot==20.7    # Alerts
```

### Code Style
- **Type hints** everywhere (Python 3.12+ syntax)
- **Docstrings** for all classes/functions (Google style)
- **Black** formatter (88 char line length)
- **Pytest** for all tests

---

## 📋 Development Workflow

### When Starting a New Task
1. **Check `docs/task.md`** for current task status
2. **Read `docs/AMR-QTS_System_Plan_v3.md`** for system requirements
3. **Check `config/settings.py`** for parameter values (DO NOT hardcode parameters)
4. **Run existing tests** before making changes: `pytest tests/`
5. **Create feature branch** if significant change: `git checkout -b feature/task-name`

### When Writing Code
- **Import from config:** Always use `from config.settings import PARAM_NAME`
- **Logging:** Use Python `logging` module, configured in each module
- **Error handling:** Wrap risky operations in try/except, log errors, don't crash silently
- **No magic numbers:** If a threshold/parameter is used, it should be in `config/settings.py`
- **Vectorized operations:** Use pandas/numpy vectorization, avoid Python loops on dataframes

### When Testing Edge/Strategy
1. **Never optimize parameters first** — use defaults from plan
2. **Always test on validation set** (30% holdout, never touched during development)
3. **Document assumptions** — if a test depends on a data assumption, write it down
4. **Save results** — all backtest results go in `reports/backtest_results/`

### When Committing
- **Descriptive commits:** `git commit -m "feat: add signal decay curve test for Module 1"`
- **Commit often:** Small, logical commits > giant "finished task" commits
- **Update task.md:** Mark tasks as complete in `docs/task.md`

---

## 🔑 Key Concepts & Terminology

### Regime
A market state (trending, ranging, high volatility). The HMM classifies each H1 bar into one of 3 states based on 8 features. **Critical:** Regimes are probabilistic (not binary), so we get a probability distribution over states.

### Edge
A trading signal that has **positive expectancy** (expected value > 0). Not just "profitable in backtest" — must pass validation tests (random benchmark, signal decay, PnL attribution).

### Portfolio-Level Risk
Instead of sizing each trade independently (e.g., "0.5% risk per trade"), we allocate a **total daily risk budget** (1.5%) across all active modules based on regime confidence. Example: If HMM says 85% confident in trending, allocate 85% of budget to Module 1.

### Walk-Forward Analysis
Train model on period 1, test on period 2. Roll forward: train on period 2, test on period 3. Repeat across entire dataset. This simulates "retraining the model every X months" and catches overfitting that a single train/test split misses.

### Deflated Sharpe Ratio (DSR)
Accounts for **multiple testing bias**. If you tested 10 variations of a strategy, your "best" Sharpe is inflated by selection bias. DSR adjusts for this, giving you a confidence level (e.g., "95% confident this Sharpe is genuinely positive").

### CPCV (Combinatorial Purged Cross-Validation)
Advanced cross-validation that:
1. Splits data into N groups (e.g., 6 bi-monthly chunks)
2. Tests all combinations of train/test splits
3. "Purges" overlapping samples to prevent leakage
4. Returns a **distribution of Sharpe ratios**, not a single number

### HMM (Hidden Markov Model)
A probabilistic model that assumes the market is in one of several "hidden states" (trending, ranging, high vol), and we observe features (ADX, ATR, etc.) that are generated by those states. The model learns:
- **Emission probabilities:** P(feature | state)
- **Transition probabilities:** P(state_t+1 | state_t)
- **State probabilities:** P(state | all observed features)

**Why use HMM instead of rules?** Rules like "ADX > 25 = trending" are brittle. HMM learns from data, handles uncertainty, and gives probabilities instead of hard classifications.

---

## ⚠️ Common Pitfalls & Gotchas

### Data Leakage
- **Forward-looking bias:** Never use future data to make past decisions. Example: Don't use "close[t+1]" to generate a signal at time t.
- **Train/test contamination:** Validation set (30% holdout) must **never** be used for parameter tuning. Only test on it once at the end.
- **Indicator calculation:** Some indicators (EMA, ATR) need a warmup period. First 50 bars of EMA(50) are invalid — drop them.

### Overfitting Red Flags
- Sharpe ratio > 3 (unrealistic)
- Win rate > 70% (suspicious)
- Too many parameters (>10 tunable parameters = danger zone)
- Performance degrades on validation set
- Strategy works on one pair but fails on similar pairs

### HMM-Specific Issues
- **Convergence failure:** HMM training can fail to converge. Solution: Try different random seeds, increase max iterations, check feature scaling.
- **State label switching:** HMM doesn't guarantee State 0 = "trending" across different training runs. Solution: Post-process state labels by mapping based on ADX/ATR characteristics.
- **Too few/too many states:** Start with 3 states. If regime boundaries are unclear, try 4. If HMM always stays in 1 state, try 2.

### MT5 Integration (Phase 3)
- **Python ↔ MQL5 bridge:** Two options: file bridge (Python writes CSV, EA reads) or socket bridge (TCP server). Start with file bridge (simpler).
- **Time zones:** MT5 uses broker time, Python uses UTC. Always convert to UTC for consistency.
- **Symbol naming:** MT5 symbols vary by broker (e.g., "EURUSD" vs "EURUSDm"). Check broker's symbol list.

---

## 📊 Parameter Reference (Quick Lookup)

**All parameters are in `config/settings.py`**. Never hardcode. Here are the critical ones:

### Risk Parameters
```python
BASE_RISK_PERCENT = 0.5          # Risk per trade
DAILY_LOSS_CAP = 3.0             # Daily max loss %
MAX_OPEN_TRADES = 3              # Simultaneous positions
TOTAL_DAILY_BUDGET = 1.5         # Portfolio risk budget %
```

### Regime Detection (HMM)
```python
HMM_N_STATES = 3                 # Number of hidden states
HMM_CONFIDENCE_THRESHOLD = 0.70  # Min probability to trade
HMM_N_ITER = 100                 # Max training iterations
HMM_FEATURES = ['returns', 'realized_vol', 'adx', 'adx_slope', 
                'atr_ratio', 'ema_proximity', 'dxy_trend', 'vix_level']
```

### Module 1 (Trend)
```python
TREND_ADX_THRESHOLD = 25         # Min ADX for trend
TREND_TRAIL_ATR_MULT = 2.0       # Trail stop multiplier
TREND_TP_RR = 3.0                # Take profit (risk:reward)
```

### Module 2 (Mean Reversion)
```python
MR_BB_PERIOD = 20                # Bollinger Band period
MR_BB_STD = 2.0                  # Bollinger Band std dev
MR_MAX_ADX = 25                  # Max ADX for ranging
MR_STOP_ATR_MULT = 1.5           # Stop loss multiplier
```

### Module 3 (High Vol)
```python
HV_ATR_THRESHOLD = 1.5           # Min ATR ratio for high vol
HV_TP_ATR_MULT = 1.0             # Quick profit take
HV_TRAIL_ATR_MULT = 1.0          # Tight trail
```

### Validation
```python
TRAIN_TEST_SPLIT = 0.70          # 70% train, 30% test
CPCV_N_SPLITS = 6                # Number of CPCV folds
MONTE_CARLO_RUNS = 10000         # Monte Carlo iterations
```

---

## 🎓 Key Resources & References

### Books (System Design Philosophy)
- **Marcos López de Prado** — *Advances in Financial Machine Learning*
  - CPCV, Deflated Sharpe, Minimum Backtest Length formulas
  - Chapter 12 (Cross-Validation), Chapter 14 (Backtesting)
- **Ernest Chan** — *Quantitative Trading* & *Algorithmic Trading*
  - Walk-forward analysis, mean reversion strategies
- **Andreas Clenow** — *Following the Trend*
  - Trend-following modules, position sizing

### Papers
- López de Prado (2014) — "The Deflated Sharpe Ratio"
- Bailey et al. (2014) — "The Probability of Backtest Overfitting"

### Online Resources
- **hmmlearn documentation:** https://hmmlearn.readthedocs.io/
- **QuantConnect forums:** (for algo trading best practices)
- **Elite Trader forums:** (institutional validation techniques)

---

## 🔧 Troubleshooting Common Issues

### "HMM not converging"
- Check feature scaling — standardize all features to mean=0, std=1
- Increase `n_iter` in HMM config (try 200)
- Try different random seed: `HMM(random_state=42)`
- Verify data quality — missing values break HMM

### "Backtest shows profit, validation set fails"
- **Classic overfitting.** Solution: Walk-forward analysis will catch this.
- Check if you accidentally used validation set for parameter tuning
- Check if indicator calculation is forward-looking

### "Module backtest shows negative expectancy"
- **This is EXPECTED sometimes.** Not all modules will have positive expectancy in isolation.
- If all 3 modules are negative → system has no edge, back to research phase
- If 1–2 modules are positive → proceed, regime switching adds value

### "MT5 data download fails"
- Check MT5 terminal is running and logged in
- Verify symbol name matches broker's symbol list
- Check `Market Watch` in MT5 — symbol must be visible

### "Git conflicts when switching machines"
- **DO NOT** commit data files (`.gitignore` handles this)
- **DO** commit code, configs, notebooks (with outputs cleared)
- Use `git pull --rebase` to avoid merge commits

---

## 📞 How to Use This Document

### For Claude (or any AI assistant)
When you (AI) receive a new task in this project:
1. **Read this file first** (PROJECT_CONTEXT.md)
2. Check `docs/task.md` for current task status
3. Refer to `docs/AMR-QTS_System_Plan_v3.md` for detailed specs
4. Check `config/settings.py` for current parameter values
5. **Ask clarifying questions** if anything is unclear before coding

### For Human Developer (Me)
When switching tools or resuming work:
1. Share this file with the new AI assistant: "Read PROJECT_CONTEXT.md first"
2. Point to specific section if needed: "See 'Current Development State' for where we are"
3. Update this file when major architecture decisions change

### What to Update in This File
- **Current Phase/Task** whenever you move to a new task
- **Phase Progress** (✅/🔄/📅) as tasks complete
- **Architecture** if Layer structure changes
- **Key Concepts** if new terminology emerges
- **Troubleshooting** when you discover new pitfalls

---

## 🚨 Critical Reminders

1. **No parameter optimization until edge is proven** — Defaults first, validate, then optimize if needed
2. **Validation set is sacred** — Never touch it until final test
3. **HMM states are probabilistic** — Always check `regime_probability`, not just `regime_label`
4. **Risk layer overrides strategy layer** — If risk says no, strategy doesn't matter
5. **Phase 1 is about research** — It's OK if things don't work. Document what fails and why.
6. **Complexity must earn its place** — If simpler model gets 90% of complex model's performance, use simpler
7. **This is a marathon, not a sprint** — 5 phases, 6+ months to deployment

---

*Last Updated: February 28, 2026*  
*For: Phase 1 — Module Isolation Backtesting*  
*Next Update: When Phase 1 completes*
