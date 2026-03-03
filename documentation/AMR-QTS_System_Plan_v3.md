# Adaptive Multi-Regime Quantitative Trading System (AMR-QTS)
### Master Plan v3.0 — Institutional Techniques at Retail Scale

> [!NOTE]
> v3.0 integrates all 6 hedge fund approaches from the [Deep Critique](file:///C:/Users/ansar/.gemini/antigravity/brain/61e82b78-01a4-4d04-b656-c02d1368602c/AMR-QTS_Deep_Critique.md) — adapted for retail infrastructure (no Bloomberg, no CME feeds, no co-location). Changes from v2.0 are marked **[v3]**.

---

## OBJECTIVE

**Primary Goal:** Generate consistent, compounding returns on personal capital through prop firm scaling.

**Design Philosophy:**
- **[v3] Alpha-first** — prove the edge exists *before* engineering around it
- Regime-adaptive via probabilistic models, not fixed thresholds
- Risk-first architecture — survival before growth
- Portfolio-level thinking, not isolated trade decisions
- Fully systematic — zero discretionary interference
- Statistically validated to institutional rigor standards

---

## ALPHA MODEL

### Edge Hypotheses

| # | Hypothesis | Factor | Free Data Source |
|---|---|---|---|
| 1 | **Momentum persistence** — trending regimes show continuation over 1–4 hour windows due to institutional order flow building over time | Momentum | MT5 OHLCV |
| 2 | **Mean reversion in constrained ranges** — 2σ deviation from mean with no directional flow reverts due to market-making behavior | Mean Reversion | MT5 OHLCV |
| 3 | **[v3] Volatility regime premium** — correctly classifying regime (not just trending/ranging, but the *probability* of being in that regime) adds alpha by avoiding false signals | Regime timing | MT5 OHLCV + DXY |

### Phase 1 Validation Requirements

| Test | Tool | Pass Criteria |
|---|---|---|
| Random entry benchmark | Custom Python | Actual entries must outperform random by ≥ 15% on expectancy |
| Signal decay curve | Custom Python | Favorable excursion must increase for 10+ bars after entry |
| PnL attribution | Custom Python | Entry timing must contribute ≥ 20% of total PnL |
| Remove top 10% trades | Custom Python | System remains profitable |
| **[v3] Naked signal test** | Custom Python | Test each entry signal with no risk management — just entry → fixed hold → exit. If this is negative, the entry itself has no edge. Still useful as a risk-alpha system but changes how you think about the architecture. |

---

## INSTRUMENT SELECTION

### Tier 1 — Core (Always Active)

| Pair | Execution TF | Modules |
|---|---|---|
| **EURUSD** | 15m | All |
| **GBPUSD** | 15m | All |

### Tier 2 — After 3+ Months Validated

| Pair | Execution TF | Modules |
|---|---|---|
| **USDJPY** | 15m | Trend, High Vol |
| **GBPJPY** | 15m | Trend, High Vol (50% position size) |

### Tier 3 — Optional

| Pair | Execution TF | Modules |
|---|---|---|
| **XAUUSD** | 15m | High Vol only |

### **[v3] Cross-Asset Regime Signals (Free Data)**

These are NOT traded — they are used as *inputs to the regime detector*:

| Instrument | Source | What It Tells You |
|---|---|---|
| **DXY (US Dollar Index)** | TradingView free / MT5 symbol `USDX` | Dollar-wide trend vs range — if DXY is trending, all USD pairs are more likely in trend regime |
| **VIX (or VIXM proxy)** | Yahoo Finance / yfinance | Global risk appetite — VIX > 25 = risk-off, increases volatility regime probability |
| **US10Y yield** | FRED API (free) / yfinance | Rate differential driver — rapidly moving yields can cause regime breaks before FX price shows it |

> These cross-asset signals feed into the HMM as additional observable features. They cost nothing but add early-warning capability that most retail systems lack.

### Timeframe Stack

```
Daily      → Overall bias & key S/R
H4         → Regime confirmation, structural trend (HH/HL)
H1         → Regime classification (HMM + indicators)
15m        → Entry execution
```

### Active Sessions

| Session | Pairs | Modules |
|---|---|---|
| London Open (07:00–10:00 GMT) | EURUSD, GBPUSD | Breakout + trend |
| London/NY Overlap (12:00–16:00 GMT) | All Tier 1+2 | All |
| Asian (00:00–07:00 GMT) | USDJPY | Mean reversion only |

---

## SYSTEM ARCHITECTURE — 5 LAYERS

> [!IMPORTANT]
> v3 adds **Layer E — Execution Layer** and restructures Layer B into a probabilistic model. The architecture is now 5 layers.

---

### LAYER A — Risk Governance (Overrides All)

#### A1. Risk Per Trade
- Base risk: **0.5% equity**
- Max risk: **1%** — after equity ATH + 3 months consistency

#### A2. Daily Loss Cap
- Hard stop at **3% equity loss** → disabled for the day

#### A3. Open Exposure
- Max **3 simultaneous trades**
- Total exposure ≤ **2% equity**
- **[v3]** Total exposure is now calculated at the *portfolio level*, not per-trade — see Layer B2

#### A4. Correlation Control
- **Phase 1–4:** Max 1 USD-directional trade, max 1 GBP pair
- **[v3] Phase 5+:** Rolling 20-day correlation matrix. Second correlated trade allowed only if correlation < 0.7. If allowed, combined size reduced by correlation factor

#### A5. Volatility Safety Switch
- H1 ATR(14) > 2× 30-day SMA → reduce size 50%, disable mean reversion, tighten existing stops to 1× ATR

#### A6. News Filter
- No entries 30 min before / 15 min after high-impact events
- Existing trades: stops manage them

#### A7. Session Filter
- No entries in last 60 min before session close
- No trades Friday 20:00+ GMT / Sunday before 22:00 GMT

#### A8. Regime Transition Protocol

| Transition | Action |
|---|---|
| TREND → RANGE/NEUTRAL | Tight ATR × 1.0 trail, exit if no progress in 8 H1 bars |
| RANGE → TREND | Exit mean reversion trades immediately |
| ANY → HIGH VOL | Tighten all stops to ATR × 1.0 |
| HIGH VOL → ANY | Let existing trades run |

---

### LAYER B — Regime Detection Engine **[v3 — REBUILT AS PROBABILISTIC MODEL]**

> [!IMPORTANT]
> **Hedge Fund Approach #2 fully implemented.** The regime detector is now a Hidden Markov Model (HMM) instead of fixed ADX thresholds. This is implementable for free using Python's `hmmlearn` library.

#### B1. Hidden Markov Model (HMM) Regime Detector

**What is HMM in plain language:** Instead of saying "ADX > 25 = trending," the HMM looks at *multiple features simultaneously* and says "given everything I see right now, there's a 78% probability we're in a trending state, 15% ranging, 7% high-vol." It learns the transition patterns — e.g., how often trends become ranges, how long each state lasts — from historical data.

**Observable Features (inputs to HMM):**

| Feature | Calculation | Source |
|---|---|---|
| Returns | Log returns of H1 close | MT5 data |
| Realized volatility | Rolling 20-bar std dev of H1 returns | MT5 data |
| ADX(14) | Standard directional index, H1 | MT5 data |
| ADX slope | ADX current − ADX 3 bars ago | MT5 data |
| ATR ratio | ATR(14) / ATR(14) 30-day SMA | MT5 data |
| EMA proximity | abs(EMA50 − EMA200) / ATR(14), H1 | MT5 data |
| **[v3] DXY trend** | 20-bar rate of change of DXY | MT5 / TradingView |
| **[v3] VIX level** | Current VIX (daily, carried forward to H1) | yfinance (free) |

**Hidden States (what the HMM classifies):**

| State | Description | Active Module |
|---|---|---|
| State 0 | TRENDING LOW VOL | Module 1 |
| State 1 | RANGING LOW VOL | Module 2 |
| State 2 | HIGH VOLATILITY | Module 3 |

**Decision Rules:**
```
regime_probability = hmm.predict_proba(current_features)

IF max(regime_probability) > 0.70:
    → Activate corresponding module
    
IF max(regime_probability) < 0.70:
    → NEUTRAL — no new entries (high uncertainty)
    
Transition smoothing:
    → Require 2 consecutive H1 bars of >70% probability
      before switching regime (prevents whipsawing)
```

**Training:**
- Train on 2+ years of H1 data in Phase 1
- Use Baum-Welch algorithm (built into hmmlearn)
- Validate with walk-forward: retrain every 6 months on rolling data
- 3 hidden states is the starting point — test 4 states (splitting trending into up/down) if 3 is too coarse

**Fallback:** If HMM is unreliable on live data, the v2 rule-based detector (ADX slope + ATR ratio) serves as the backup. Both run in parallel during Phase 4 demo — compare accuracy.

#### B2. Portfolio-Level Risk Budgeting **[v3 — NEW]**

> **Hedge Fund Approach #3 implemented.** Instead of "0.5% per trade" independently, allocate risk at the portfolio level.

**Concept:** The system has a total daily risk budget of **1.5% equity** (half the daily cap of 3%, providing margin of safety). This budget is *allocated* to strategy modules based on current regime confidence:

```
Total daily risk budget: 1.5%

Allocation by regime:
  IF TRENDING with >85% confidence:
    → Trend module gets 1.0% budget, Mean Rev gets 0.0%, High Vol gets 0.5%
    
  IF RANGING with >85% confidence:
    → Trend gets 0.0%, Mean Rev gets 1.0%, High Vol gets 0.5%
    
  IF HIGH VOL with >85% confidence:
    → Trend gets 0.0%, Mean Rev gets 0.0%, High Vol gets 1.0%
    (remaining 0.5% unallocated — safety buffer)
    
  IF MIXED confidence (<85% on any):
    → Split evenly: 0.5% / 0.5% / 0.5%
    → But NEUTRAL modules get 0.0%
```

**Per-trade risk within budget:**
- Each module can take max **0.5% per trade** (unchanged)
- But total module exposure capped by its allocated budget
- Example: Trend module has 1.0% budget → can take 2 trades at 0.5% each

**Why this matters:** In simple per-trade risk, you might stack 3 trend trades at 0.5% each = 1.5% exposure to one regime. With portfolio budgeting, you consciously decide: "trending is high confidence right now, so it gets more of the risk budget." This is how hedge funds prevent concentration risk.

---

### LAYER C — Strategy Modules

---

#### MODULE 1 — Trend Continuation

**Activation:** TRENDING regime with >70% HMM probability

**HTF Confluence:**
- H4 structure trending (HH/HL or LH/LL)
- Price above H1 EMA(200) for longs / below for shorts

**Entry (15m):**
- Break and close above 20-bar high (longs) / below 20-bar low (shorts)
- ATR expansion: current bar range > 1.5× avg of last 5 bars
- RSI(14): 45–70 for longs, 30–55 for shorts
- No entry within 1× H4 ATR of major H4 S/R level
- **[v3]** Entry via limit order at breakout level (see Layer E)

**Stop Loss:** ATR(14) × 1.5 from entry

**Exit:**
- Primary: 1:2 RR
- ATR trailing activated at 1:1
- Excursion exit: retrace 50%+ from MFE before 1R → exit

**Risk:** 0.5% base (within Module 1's portfolio budget)

---

#### MODULE 2 — Mean Reversion

**Activation:** RANGING regime with >70% HMM probability

**HTF Confluence:**
- H4 price inside established range
- H1 EMA proximity < 0.5 (ATR-normalized)

**Entry (15m):**
- RSI(14) < 30 → Long / RSI(14) > 70 → Short
- Price at Bollinger Band extreme (2σ)
- Confirmation: next candle closes back inside band
- **[v3]** Entry via limit order at band level (see Layer E)

**Stop Loss:** ATR(14) × 1.2 beyond BB extreme

**Exit:**
- Primary: Bollinger midline
- Min RR: 1:1.5
- Time exit: 20 bars → exit at market

**Risk:** 0.5% base

**Blocks:** Disabled if ATR ratio > 1.5, if H4 trending, or if regime transitions to TRENDING.

---

#### MODULE 3 — High Volatility Protocol

**Activation:** HIGH VOL regime with >70% HMM probability

**HTF Confluence:** H4 directional break with momentum

**Entry (15m):**
- 20-bar high/low breakout
- Bar range (H−L) > 2× avg of last 20 bars
- Candle body > 60% of total range
- ATR current > previous ATR by 20%+
- **[v3]** Entry via limit order at breakout level (see Layer E)

**Stop Loss:** ATR(14) × 2.0

**Exit:** 1:1.5 RR minimum. No trailing stop.

**Risk:** 0.25% (mandatory 50% reduction)

---

### LAYER D — Equity Curve & Performance Monitoring **[v3 — MAJOR UPGRADE]**

> **Hedge Fund Approach #6 fully implemented.** Replaces quarterly manual review with daily automated monitoring.

#### D1. Equity Curve Control (from v2)
- 20-period SMA of equity curve
- Equity < SMA(20) → reduce all sizes by 50%
- New equity ATH → restore base risk

#### D2. Automated Performance Monitor **[v3 — NEW]**

A Python script running daily (or a dashboard) that checks:

```python
class PerformanceMonitor:
    """Runs daily after market close. Uses only trade log CSV."""
    
    def check_sharpe_deviation(self, realized_trades, backtested_sharpe):
        """
        Compare rolling 30-day realized Sharpe vs backtested.
        ALERT if realized < 50% of backtested for 15+ consecutive days.
        SHUTDOWN if this persists for 30+ days.
        """
    
    def check_regime_accuracy(self, predicted_regimes, actual_outcomes):
        """
        What % of regime predictions led to profitable trades?
        ALERT if accuracy drops below 55% over 30-day window.
        Signals HMM may need retraining.
        """
    
    def check_fill_deviation(self, expected_entries, actual_fills):
        """
        Track slippage: actual fill - expected entry.
        ALERT if avg slippage > 0.5 pips consistently.
        May indicate broker execution issues.
        """
    
    def check_module_contribution(self, trades_by_module):
        """
        Is each module contributing positive PnL?
        ALERT if any module is net negative over 60-day window.
        Consider disabling that module.
        """
    
    def check_signal_decay(self, recent_signals):
        """
        Has the edge decayed? Compare signal decay curve
        of last 100 trades vs backtest baseline.
        ALERT if mean favorable excursion at bar 10 dropped > 30%.
        """
```

**Alert Levels:**

| Level | Condition | Action |
|---|---|---|
| 🟡 WARNING | 1 metric triggered | Log, investigate manually, no system change |
| 🟠 ALERT | 2+ metrics triggered | Reduce risk by 50%, investigate urgently |
| 🔴 SHUTDOWN | Sharpe deviation > 30 days OR 3+ metrics triggered | Pause system entirely, retrain HMM, re-validate in Python |

**Delivery:** Telegram bot notification + CSV log. No paid services needed.

---

### LAYER E — Execution Layer **[v3 — ENTIRELY NEW]**

> **Hedge Fund Approach #4 implemented at retail scale.** Replaces "market order on signal" with structured execution.

#### E1. Order Type Selection

| Module | Order Type | Why |
|---|---|---|
| Module 1 (Trend) | **Buy/Sell Stop** at breakout level | Places order at the 20-bar high/low *before* the break happens. Fills on the break itself rather than chasing a close. Reduces slippage. |
| Module 2 (Mean Rev) | **Buy/Sell Limit** at Bollinger Band level | If price is approaching the band, place limit at the band. Gets better fill than waiting for close + market order. |
| Module 3 (High Vol) | **Buy/Sell Stop** at breakout level | Same as Module 1 but with wider stop gap for volatility |

#### E2. Order Management Rules

```
1. Pending order expires after 4 H1 bars (4 hours) if not filled
   → prevents stale orders filling in wrong regime
   
2. If regime changes before fill → cancel pending order immediately

3. Maximum slippage tolerance: 1.0 pip
   → if fill deviates > 1.0 pip from order price, exit immediately
   (indicates abnormal conditions — news, gap, liquidity void)
   
4. No more than 2 pending orders at any time per pair
```

#### E3. Slippage Modeling (Phase 1 Python)

```python
def apply_realistic_execution(signal, spread, slippage_model):
    """
    In backtest, don't assume perfect fills.
    
    Model:
    - Entry: signal price + spread + random(0, 0.3 pips)
    - Stop hit: stop price + random(0, 0.5 pips) adverse
    - Target hit: target price - random(0, 0.2 pips) adverse
    
    This reduces backtest fantasy by ~5-15% which is realistic.
    """
```

---

## DEVELOPMENT ROADMAP — 5 PHASES

---

### PHASE 1 — Research & Backtesting in Python (8–10 Weeks)

> Duration increased from 6–8 to 8–10 weeks to account for HMM development and institutional-grade validation.

#### Step 1: Data Collection
```python
# MT5 Python API for OHLCV — EURUSD, GBPUSD (minimum)
# Min 3 years of H1, 15m, 5m data
# Cross-asset: DXY (MT5 or TradingView), VIX (yfinance)
# Clean: remove zero-vol bars, holiday gaps, data errors
# Add: realistic spread + slippage model from Layer E3
```

#### Step 2: Build HMM Regime Detector
```python
from hmmlearn.hmm import GaussianHMM

# 1. Engineer features from H1 data:
#    returns, realized_vol, adx, adx_slope, atr_ratio,
#    ema_proximity, dxy_roc, vix_level

# 2. Fit HMM with 3 states on training data
hmm = GaussianHMM(n_components=3, covariance_type='full', n_iter=200)
hmm.fit(training_features)

# 3. Label states by inspecting means:
#    - State with highest return variance = HIGH_VOL
#    - State with highest mean abs return = TRENDING
#    - State with lowest mean abs return = RANGING

# 4. Validate: walk-forward retrain every 6 months
# 5. Compare accuracy vs rule-based detector (v2) on same data
```

#### Step 3: Build Strategy Modules
```python
def trend_strategy(data_15m, data_h1, regime_prob) -> list[Signal]:
    """Requires regime_prob['trending'] > 0.70"""

def mean_reversion_strategy(data_15m, data_h1, regime_prob) -> list[Signal]:
    """Requires regime_prob['ranging'] > 0.70"""

def high_vol_strategy(data_15m, data_h4, regime_prob) -> list[Signal]:
    """Requires regime_prob['high_vol'] > 0.70"""

def portfolio_risk_manager(signals, equity, budget_allocation, 
                           correlations, daily_loss) -> list[SizedOrder]:
    """
    Portfolio-level sizing:
    1. Check total budget remaining for each module
    2. Check correlation with existing positions
    3. Apply execution model (stop/limit order pricing)
    4. Return sized orders or empty list if blocked
    """
```

#### Step 4: Isolate Backtest Each Module

| Metric | Pass Threshold |
|---|---|
| Profit Factor | > 1.3 |
| Max Drawdown | < 15% |
| Win Rate | > 40% |
| Sharpe Ratio | > 0.8 |
| Expectancy | > 0 per trade |
| Stability | Profitable across all 3 years independently |

#### Step 5: Edge Validation

| Test | Pass Criteria |
|---|---|
| Random entry benchmark | Actual entries beat random by ≥ 15% on expectancy |
| Signal decay curve | MFE increasing for 10+ bars |
| PnL attribution | Entry timing ≥ 20% of total PnL |
| Remove top 10% trades | Still profitable |
| Naked signal test | Entry → fixed hold → exit shows directional bias |

#### **[v3] Step 6: HMM vs Rules Comparison**

Run both regime detectors on the same data:

| Metric | Rules (v2) | HMM (v3) |
|---|---|---|
| Regime accuracy (% of trades profitable in detected regime) | ? | ? |
| False regime rate (trades taken in wrong regime) | ? | ? |
| System Sharpe using this detector | ? | ? |
| Regime change lag (bars late vs actual structural change) | ? | ? |

> **Decision rule:** If HMM outperforms rules by < 10% on all metrics, keep the simpler rule-based detector. Complexity must earn its place. If HMM outperforms by ≥ 10%, adopt HMM as primary with rules as fallback.

---

### PHASE 2 — Combined System + Institutional Validation (4–6 Weeks)

> Duration increased to accommodate CPCV and deflated Sharpe testing.

#### Tests (v2 retained)
1. Walk-Forward: 6-month train → 2-month forward → ≥ 70% windows profitable
2. Monte Carlo: 1,000 iterations, 95th percentile DD < 20%
3. Robustness: spread +50%, params ±20%, remove best 20 trades
4. Regime-conditional Sharpe: each regime must have positive Sharpe individually

#### **[v3] Institutional-Grade Statistical Tests**

> **Hedge Fund Approach #5 fully implemented.** All tools are free Python.

**Test A: Combinatorial Purged Cross-Validation (CPCV)**

```python
# Instead of simple 70/30 split, use CPCV from Marcos López de Prado
# Library: none needed, implement from "Advances in Financial ML" Ch. 12
# Or use: mlfinlab (pip install mlfinlab, free/open source)

# How it works:
# - Split data into N groups (e.g., 6 bi-monthly groups across 3 years)
# - Test all combinations of train/test splits
# - Purge overlapping samples to prevent leakage
# - Result: distribution of Sharpe ratios, not a single number

# Pass criteria:
# - Median Sharpe across all CPCV folds > 0.5
# - No fold has Sharpe < -0.5 (no catastrophic failure scenario)
```

**Test B: Deflated Sharpe Ratio**

```python
# Accounts for multiple testing bias: if you tested 10 strategy
# variations, your "best" Sharpe is inflated by selection bias.
# 
# Formula (López de Prado, 2014):
# DSR = Prob(Sharpe > 0 | number of trials, skewness, kurtosis)
#
# Implementation: ~20 lines of Python (scipy.stats)
#
# Pass criteria:
# - DSR > 0.95 (95% confidence the Sharpe is genuinely positive)
# - Track N_trials honestly: every parameter you changed counts
```

**Test C: Minimum Backtest Length**

```python
# Formula: MinBTL = (1 + (1 - skew * SR) + (kurtosis * SR²)/4)
#                    * (z_alpha / SR)² years
#
# Purpose: tells you if 3 years of data is even ENOUGH to validate
#          your strategy's Sharpe ratio statistically
#
# If MinBTL > 3 years → your backtest is too short to be trustworthy
# → need more data or a stronger signal
```

---

### PHASE 3 — MT5 EA Architecture (4–6 Weeks)

#### File Structure
```
AMR-QTS/
├── MainEA.mq5
├── include/
│   ├── RegimeDetector.mqh     ← Rule-based (always runs as fallback)
│   ├── TrendModule.mqh
│   ├── MeanReversionModule.mqh
│   ├── HighVolModule.mqh
│   ├── RiskManager.mqh        ← Portfolio-level budgeting
│   ├── EquityCurveControl.mqh
│   ├── NewsFilter.mqh
│   ├── TransitionManager.mqh
│   └── ExecutionManager.mqh   ← [v3] Stop/limit order logic
├── python/
│   ├── hmm_model.pkl          ← [v3] Serialized trained HMM
│   ├── regime_server.py       ← [v3] Runs HMM, serves regime via socket/file
│   └── monitor.py             ← [v3] Daily performance monitor + alerts
└── logs/
    └── trades_log.csv
```

**[v3] HMM Integration Pattern:**

The HMM runs in Python (hmmlearn doesn't have an MQL5 equivalent). Two options:

| Option | How | Pros | Cons |
|---|---|---|---|
| **File bridge** | Python writes regime + probability to a CSV every H1 bar. EA reads the file. | Simple, no networking | 1-bar delay possible |
| **Socket bridge** | Python runs a local TCP server. EA sends features, receives regime. | Real-time, no delay | More complex to build |

> Start with file bridge in Phase 4 (simpler). Upgrade to socket bridge in Phase 5 if latency matters.

#### Input Parameters
```mql5
input bool   UseBreakout          = true;
input bool   UseMeanReversion     = true;
input bool   UseVolatilityFilter  = true;
input bool   UseEquityCurveCtrl   = true;
input bool   UseNewsFilter        = true;
input bool   UseHMMRegime         = true;    // [v3]
input bool   UseLimitExecution    = true;    // [v3]
input double BaseRiskPercent      = 0.5;
input double TotalDailyBudget     = 1.5;     // [v3] portfolio budget %
input int    MaxDailyLossPercent  = 3;
input int    MaxOpenTrades        = 3;
input double MaxSlippagePips      = 1.0;     // [v3]
input int    PendingOrderExpiry   = 4;       // [v3] hours
```

#### Logging
Every trade logs: timestamp, pair, module, regime state, **regime probability**, entry price, order type (stop/limit/market), expected vs actual fill, SL, TP, lot size, exit price, PnL, daily DD, ATR, ADX.

#### Alerting
Telegram bot: daily cap hit, equity ATH, regime change, Sharpe deviation, HMM confidence drop, fill slippage warning, EA error.

---

### PHASE 4 — Demo Forward Test (3 Months Minimum)

**Rules:** Zero parameter changes. Zero manual trades.

| Metric | Target |
|---|---|
| Equity curve slope | Positive |
| Max daily DD | < 3% |
| Max overall DD | < 8% |
| Monthly return | 2–7% |
| Realized vs backtested Sharpe | Within 1σ |
| **[v3] HMM vs rules accuracy** | Track both, compare |
| **[v3] Avg fill slippage | < 0.3 pips EURUSD |

**[v3] Run both detectors in parallel:**
- HMM provides regime classification
- Rule-based provides regime classification
- EA trades based on the primary (HMM or rules — whichever won Phase 1 Step 6)
- Log both predictions — compare accuracy at end of 3 months

---

### PHASE 5 — Prop Firm Deployment

**Challenge risk:** 0.3% base
**No trades:** Friday 18:00+ GMT, 30 min around high-impact news

**Scaling:**

| Stage | Risk | Condition |
|---|---|---|
| Survival | 0.5% | 3–6 months record |
| Scaling | 0.75% | Consistent profitability + equity ATH |
| Diversification | 0.75% | Tier 2 pairs, 2nd prop account, dynamic correlation matrix |

---

## PERFORMANCE PROFILE (Realistic)

| Metric | Target |
|---|---|
| Win Rate | 45–58% |
| Avg RR | 1.5–2.0 |
| Monthly Return | 3–7% |
| Max Drawdown | 5–8% |
| Profit Factor | > 1.3 |
| **[v3] DSR (Deflated Sharpe)** | > 0.95 |

---

## CORE PRINCIPLES

1. Risk management > strategy quality
2. Regime adaptation > single edge
3. Robustness > optimization
4. Survival > growth
5. Statistical validation > gut feeling
6. Know your alpha — if you can't explain why the trade makes money, don't take it
7. **[v3] Complexity must earn its place** — simpler model wins unless complex model outperforms by ≥ 10%

---

## PYTHON LIBRARIES REQUIRED (ALL FREE)

| Library | Purpose | Install |
|---|---|---|
| `MetaTrader5` | Data pull + EA bridge | `pip install MetaTrader5` |
| `hmmlearn` | Hidden Markov Model | `pip install hmmlearn` |
| `numpy`, `pandas` | Data manipulation | `pip install numpy pandas` |
| `scipy` | Deflated Sharpe, statistical tests | `pip install scipy` |
| `ta` or `ta-lib` | Technical indicators | `pip install ta` |
| `yfinance` | VIX + US10Y data (free) | `pip install yfinance` |
| `mlfinlab` (optional) | CPCV implementation | `pip install mlfinlab` |
| `python-telegram-bot` | Alert notifications | `pip install python-telegram-bot` |
| `matplotlib`, `seaborn` | Charting | `pip install matplotlib seaborn` |
| `joblib` | HMM model serialization | Built into Python |

**Total cost: $0.**

---

## CHANGELOG v2.0 → v3.0

| # | Hedge Fund Approach | What Changed | Section |
|---|---|---|---|
| 1 | Research alpha first | Naked signal test added, deeper edge validation | Alpha Model |
| 2 | Use regime models, not rules | Full HMM regime detector with 8 features including DXY/VIX | Layer B1 |
| 3 | Portfolio construction > per-trade | Portfolio risk budgeting system with regime-based allocation | Layer B2 |
| 4 | Execution as separate layer | Layer E added — stop/limit orders, slippage tolerance, pending order mgmt | Layer E |
| 5 | Extreme OOS rigor | CPCV, Deflated Sharpe, Minimum Backtest Length tests | Phase 2 |
| 6 | Automated live monitoring | PerformanceMonitor class with 5 daily checks + 3-tier alert system | Layer D2 |

---

*Plan Version: 3.0 | Updated: 2026-02-27*
