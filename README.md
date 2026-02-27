# AMR-QTS: Adaptive Multi-Regime Quantitative Trading System

> **Version 3.0** — Institutional techniques at retail scale

A fully systematic, regime-adaptive forex trading system designed for prop firm scaling. Built with probabilistic regime detection (Hidden Markov Models), portfolio-level risk management, and institutional-grade validation methods.

---

## 🎯 Project Overview

**Primary Goal:** Generate consistent, compounding returns through prop firm scaling

**Design Philosophy:**
- Alpha-first approach — prove the edge before engineering
- Regime-adaptive via probabilistic models (HMM), not fixed thresholds
- Risk-first architecture — survival before growth
- Portfolio-level thinking vs isolated trade decisions
- Fully systematic — zero discretionary interference
- Statistically validated to institutional rigor standards

---

## 📊 Current Status

**Phase:** Phase 1 — Research & Backtesting  
**Current Task:** Isolating backtest for each strategy module  
**Progress:** Setup complete, HMM regime detector built, strategy modules developed

### Completed Milestones
- ✅ Python environment setup (3.12.2)
- ✅ Project structure created
- ✅ Configuration system implemented
- ✅ Git repository initialized
- ✅ Data collection infrastructure
- ✅ HMM regime detector built
- ✅ Strategy modules implemented
- 🔄 **In Progress:** Module-level backtesting & edge validation

---

## 🏗️ Project Structure

```
AMR-QTS/
├── config/
│   ├── settings.py              # All system parameters from v3 plan
│   └── __init__.py
│
├── data/
│   ├── raw/                     # Downloaded OHLCV data
│   ├── processed/               # Cleaned & validated data
│   ├── external/                # DXY, VIX, US10Y from external sources
│   └── regime_labels/           # HMM-classified regime data
│
├── src/
│   ├── data/
│   │   ├── collectors/          # MT5, yfinance data downloaders
│   │   ├── validators/          # Data quality checks
│   │   └── preprocessors/       # Feature engineering
│   │
│   ├── regime/
│   │   ├── hmm_detector.py      # Hidden Markov Model regime classifier
│   │   ├── rule_detector.py     # Fallback rule-based detector
│   │   └── features.py          # Feature extraction (ADX, ATR, DXY, VIX)
│   │
│   ├── strategies/
│   │   ├── module1_trend.py     # Momentum persistence module
│   │   ├── module2_mean_reversion.py  # Range mean reversion
│   │   ├── module3_high_vol.py  # High volatility module
│   │   └── base_strategy.py     # Abstract strategy interface
│   │
│   ├── backtesting/
│   │   ├── engine.py            # Core backtest engine
│   │   ├── isolated_tests.py    # Individual module tests
│   │   ├── walk_forward.py      # Walk-forward analysis
│   │   └── monte_carlo.py       # Monte Carlo simulation
│   │
│   ├── risk/
│   │   ├── portfolio_manager.py # Portfolio-level risk budgeting
│   │   ├── position_sizer.py    # Dynamic position sizing
│   │   ├── drawdown_control.py  # Equity curve monitoring
│   │   └── correlation_matrix.py # Cross-pair correlation tracking
│   │
│   ├── validation/
│   │   ├── edge_tests.py        # Random entry benchmark, signal decay
│   │   ├── cpcv.py              # Combinatorial Purged Cross-Validation
│   │   ├── deflated_sharpe.py   # López de Prado Deflated Sharpe Ratio
│   │   └── robustness_checks.py # Parameter stability tests
│   │
│   ├── execution/
│   │   ├── order_manager.py     # Stop/limit order logic
│   │   ├── slippage_model.py    # Execution cost estimation
│   │   └── mt5_bridge.py        # Python ↔ MT5 communication
│   │
│   └── monitoring/
│       ├── performance_tracker.py  # Live performance monitoring
│       ├── alert_system.py      # Telegram alerts
│       └── regime_logger.py     # HMM vs rules comparison
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_regime_analysis.ipynb
│   ├── 03_strategy_development.ipynb
│   └── 04_validation_results.ipynb
│
├── tests/
│   ├── unit/                    # Unit tests for each module
│   ├── integration/             # Integration tests
│   └── backtest_scenarios/      # Historical scenario tests
│
├── mt5_ea/                      # Phase 3 MT5 Expert Advisor
│   ├── MainEA.mq5
│   ├── include/
│   │   ├── RegimeDetector.mqh
│   │   ├── TrendModule.mqh
│   │   ├── MeanReversionModule.mqh
│   │   ├── HighVolModule.mqh
│   │   ├── RiskManager.mqh
│   │   └── ExecutionManager.mqh
│   └── python/
│       ├── hmm_model.pkl        # Serialized HMM
│       └── regime_server.py     # HMM inference service
│
├── logs/
│   ├── trades/                  # Trade execution logs
│   ├── regime_changes/          # Regime transition logs
│   └── performance/             # Daily performance metrics
│
├── reports/
│   ├── backtest_results/        # Phase 1 backtest reports
│   ├── validation_reports/      # Phase 2 validation results
│   └── live_monitoring/         # Phase 4 forward test reports
│
├── docs/
│   ├── AMR-QTS_System_Plan_v3.md  # Master system plan
│   ├── task.md                  # Development task checklist
│   └── PROJECT_CONTEXT.md       # AI workflow context (for multi-tool dev)
│
├── .gitignore
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── pyproject.toml               # Project metadata & build config
```

---

## 🔬 System Architecture — 5 Layers

### Layer A: Risk Governance (Overrides All)
- Base risk: 0.5% per trade
- Daily loss cap: 3%
- Max 3 simultaneous trades
- Portfolio exposure ≤ 2%
- Correlation control, volatility safety switch
- Session/news filters, regime transition protocols

### Layer B: Regime Detection Engine
**Primary:** Hidden Markov Model (HMM) with 8 features:
- OHLC-derived: Returns, realized vol, ADX, ADX slope, ATR ratio, EMA proximity
- Cross-asset: DXY trend, VIX level

**States:**
- State 0: TRENDING LOW VOL → Module 1
- State 1: RANGING LOW VOL → Module 2
- State 2: HIGH VOLATILITY → Module 3

**Fallback:** Rule-based detector (ADX + ATR)

### Layer C: Strategy Modules
1. **Module 1 — Trend Following:** Momentum persistence with ADX confirmation
2. **Module 2 — Mean Reversion:** 2σ deviation reversion in ranges
3. **Module 3 — High Volatility:** Breakout + rapid reversal capture

### Layer D: Performance Monitoring
- Real-time Sharpe tracking with 3σ deviation alerts
- Equity curve validation (flatness detection)
- Regime misclassification monitoring
- Automated daily reporting

### Layer E: Execution Layer
- Stop/limit order placement (reduce slippage)
- Pending order management (4-hour expiry)
- Slippage tolerance checks (max 1 pip EURUSD)
- Order book depth awareness

---

## 📈 Trading Instruments

### Tier 1 — Core (Always Active)
- **EURUSD** (15m execution)
- **GBPUSD** (15m execution)

### Tier 2 — After 3+ Months Validated
- **USDJPY** (15m execution)
- **GBPJPY** (15m, 50% position size)

### Cross-Asset Regime Signals (Not Traded)
- **DXY** (US Dollar Index)
- **VIX** (Volatility Index)
- **US10Y** (US Treasury 10-Year Yield)

---

## 🛠️ Technology Stack

### Core Languages
- **Python 3.12.2** — Research, backtesting, regime detection
- **MQL5** — MT5 Expert Advisor (Phase 3+)

### Key Python Libraries
```
MetaTrader5==5.0.45        # MT5 API integration
hmmlearn==0.3.0            # Hidden Markov Models
numpy==1.26.3              # Numerical computing
pandas==2.1.4              # Data manipulation
scipy==1.11.4              # Statistical tests
ta==0.11.0                 # Technical indicators
yfinance==0.2.33           # VIX/US10Y data
matplotlib==3.8.2          # Visualization
seaborn==0.13.0            # Statistical plotting
python-telegram-bot==20.7  # Alerts
joblib==1.3.2              # Model serialization
statsmodels==0.14.1        # Time series analysis
plotly==5.18.0             # Interactive charts
```

### Development Tools
- **Git** — Version control
- **pytest** — Unit testing
- **black** — Code formatting
- **mypy** — Type checking
- **Jupyter** — Exploratory analysis

---

## 🚀 Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/AMR-QTS.git
cd AMR-QTS
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Settings
Edit `config/settings.py` with your MT5 credentials and API keys (if needed).

### 5. Download Initial Data
```bash
python scripts/download_historical_data.py
```

### 6. Train HMM Model
```bash
python scripts/train_hmm_regime_detector.py
```

---

## 📋 Development Phases

### ✅ Phase 0: Global Setup (COMPLETED)
- Python environment, project structure, Git initialization

### 🔄 Phase 1: Research & Backtesting (IN PROGRESS)
- [x] Data collection & cleaning
- [x] HMM regime detector built
- [x] Strategy modules implemented
- [ ] **Current:** Isolated backtest each module
- [ ] Edge validation tests
- [ ] HMM vs rules comparison

### 📅 Phase 2: Combined System + Validation (UPCOMING)
- Walk-forward analysis
- Monte Carlo simulation
- Robustness checks
- CPCV + Deflated Sharpe Ratio
- Regime-conditional Sharpe

### 📅 Phase 3: MT5 EA Development
- EA file structure & modules
- Python ↔ MT5 bridge (file/socket)
- Logging & alerting infrastructure

### 📅 Phase 4: Demo Forward Test
- 3-month demo run (zero parameter changes)
- Real-time performance monitoring
- HMM vs rules parallel tracking

### 📅 Phase 5: Prop Firm Deployment
- Challenge phase execution (0.3% risk)
- Scaling plan (0.5% → 0.75%)
- Multi-account diversification

---

## 📊 Validation Standards

All strategies must pass these institutional-grade tests:

### Edge Validation (Phase 1)
- **Random entry benchmark:** Actual entries must beat random by ≥15% on expectancy
- **Signal decay curve:** Favorable excursion increases for 10+ bars after entry
- **PnL attribution:** Entry timing contributes ≥20% of total PnL
- **Top 10% removal test:** System remains profitable without best trades
- **Naked signal test:** Entry signal profitable with no risk management

### Statistical Rigor (Phase 2)
- **Combinatorial Purged Cross-Validation (CPCV):** Median Sharpe > 0.5 across all folds
- **Deflated Sharpe Ratio (DSR):** > 0.95 confidence (accounts for multiple testing bias)
- **Minimum Backtest Length:** Verify 3 years is sufficient for strategy validation
- **Walk-forward analysis:** Rolling 6-month retraining, 6-month OOS test
- **Monte Carlo simulation:** 10,000 runs with 95% confidence intervals

### Live Performance (Phase 4)
- Realized vs backtested Sharpe within 1σ
- Max daily DD < 3%
- Max overall DD < 8%
- Monthly return: 2–7%
- Avg fill slippage < 0.3 pips (EURUSD)

---

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| Win Rate | 45–58% |
| Avg Risk:Reward | 1.5–2.0 |
| Monthly Return | 3–7% |
| Max Drawdown | 5–8% |
| Profit Factor | > 1.3 |
| Deflated Sharpe | > 0.95 |
| Sharpe Ratio | > 1.2 |

---

## 🔐 Core Principles

1. Risk management > strategy quality
2. Regime adaptation > single edge
3. Robustness > optimization
4. Survival > growth
5. Statistical validation > gut feeling
6. Know your alpha — if you can't explain why the trade makes money, don't take it
7. **Complexity must earn its place** — simpler model wins unless complex model outperforms by ≥10%

---

## 📝 Contributing

This is a personal trading system project. Not accepting external contributions at this time.

---

## ⚖️ License

This project is proprietary. All rights reserved.

---

## 📞 Contact

For questions about the system architecture or methodology:
- Open an issue in this repository
- Email: [your-email@example.com]

---

## 🙏 Acknowledgments

Methodology inspired by:
- **Marcos López de Prado** — *Advances in Financial Machine Learning*
- **Ernest Chan** — *Quantitative Trading* & *Algorithmic Trading*
- **Andreas Clenow** — *Following the Trend*
- Institutional risk management frameworks adapted for retail scale

---

*Last Updated: February 28, 2026*  
*Version: 3.0*  
*Status: Phase 1 — Backtest Module Isolation*
