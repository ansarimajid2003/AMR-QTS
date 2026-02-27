# AMR-QTS Development Tasks

## Save Plan & Checklist to Project
- [x] Copy System Plan v3 to project directory
- [x] Copy Checklist to project directory

## Global Setup
- [x] Create Python virtual environment (3.12.2)
- [x] Install core libraries (48 packages)
- [x] Install optional libraries (statsmodels, plotly)
- [x] Verify all imports work
- [x] Install Git + configure identity
- [x] Initial commit (15 files)
- [x] Create project folder structure
- [x] Create config/settings.py with all v3 parameters
- [x] Create .gitignore
- [x] Copy task.md to project directory

## Phase 1 — Research & Backtesting
- [ ] Data collection (EURUSD, GBPUSD, DXY, VIX, US10Y)
- [ ] Data cleaning & validation
- [ ] Build HMM regime detector
- [ ] Build strategy modules
- [ ] Isolate backtest each module
- [ ] Edge validation tests
- [ ] HMM vs rules comparison

## Phase 2 — Combined System + Validation
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation
- [ ] Robustness checks
- [ ] CPCV + Deflated Sharpe
- [ ] Regime-conditional Sharpe

## Phase 3 — MT5 EA Development
- [ ] EA file structure & modules
- [ ] Python ↔ MT5 bridge
- [ ] Logging & alerting

## Phase 4 — Demo Forward Test
- [ ] 3-month demo run
- [ ] Performance monitoring

## Phase 5 — Prop Firm Deployment
- [ ] Challenge phase execution
