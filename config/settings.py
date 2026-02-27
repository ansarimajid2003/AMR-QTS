"""
AMR-QTS Global Configuration
All times in UTC. No local time conversions anywhere.
"""

from datetime import timezone
import os

# ============================================================
# TIMEZONE — UTC EVERYWHERE
# ============================================================
TIMEZONE = timezone.utc

# ============================================================
# INSTRUMENTS
# ============================================================
TIER_1_PAIRS = ["EURUSD", "GBPUSD"]
TIER_2_PAIRS = ["USDJPY", "GBPJPY"]
TIER_3_PAIRS = ["XAUUSD"]
ALL_PAIRS = TIER_1_PAIRS + TIER_2_PAIRS + TIER_3_PAIRS

# Cross-asset regime signals (not traded)
CROSS_ASSET_SYMBOLS = {
    "DXY": "DX-Y.NYB",      # yfinance ticker for US Dollar Index
    "VIX": "^VIX",           # yfinance ticker for VIX
    "US10Y": "^TNX",         # yfinance ticker for 10Y yield
}

# ============================================================
# TIMEFRAMES
# ============================================================
ENTRY_TF = "15m"             # Primary entry timeframe
REGIME_TF = "1h"             # Regime detection timeframe
STRUCTURE_TF = "4h"          # Structural confirmation
BIAS_TF = "1d"               # Daily bias

# ============================================================
# SPREAD ASSUMPTIONS (pips, for backtesting)
# ============================================================
SPREAD_PIPS = {
    "EURUSD": 0.2,
    "GBPUSD": 0.4,
    "USDJPY": 0.3,
    "GBPJPY": 0.8,
    "XAUUSD": 2.0,
}

# Slippage model: random uniform between 0 and this value (pips)
MAX_SLIPPAGE_PIPS = 0.3

# ============================================================
# RISK PARAMETERS (Layer A)
# ============================================================
BASE_RISK_PCT = 0.5          # % equity per trade
MAX_RISK_PCT = 1.0           # Only after ATH + 3 months
DAILY_LOSS_CAP_PCT = 3.0     # Hard stop — system disabled
MAX_OPEN_TRADES = 3
MAX_EXPOSURE_PCT = 2.0       # Total exposure cap
DAILY_RISK_BUDGET_PCT = 1.5  # Portfolio-level budget

# Challenge phase risk
CHALLENGE_RISK_PCT = 0.3

# ============================================================
# REGIME DETECTION (Layer B)
# ============================================================
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25
ADX_RANGE_THRESHOLD = 20
ADX_SLOPE_BARS = 3           # Bars for ADX slope calculation
ATR_PERIOD = 14
ATR_HIGH_VOL_RATIO = 1.5     # ATR current / ATR 30-day avg
ATR_30D_WINDOW = 30          # Rolling window for ATR average
EMA_FAST = 50
EMA_SLOW = 200
EMA_PROXIMITY_THRESHOLD = 0.5  # ATR-normalized

# HMM
HMM_N_STATES = 3
HMM_MIN_CONFIDENCE = 0.70    # Minimum probability to activate module
HMM_TRANSITION_BARS = 2      # Consecutive bars needed for regime switch
HMM_RETRAIN_MONTHS = 6       # Retrain every N months in walk-forward

# ============================================================
# MODULE 1 — Trend Continuation
# ============================================================
TREND_BREAKOUT_BARS = 20     # 20-bar high/low breakout
TREND_ATR_EXPANSION = 1.5    # Bar range > 1.5× avg of 5 bars
TREND_RSI_LONG_RANGE = (45, 70)
TREND_RSI_SHORT_RANGE = (30, 55)
TREND_SL_ATR_MULT = 1.5
TREND_RR_PRIMARY = 2.0
TREND_RR_TRAIL_ACTIVATION = 1.0
TREND_MFE_RETRACE_EXIT = 0.5  # Exit if retrace 50%+ of MFE

# ============================================================
# MODULE 2 — Mean Reversion
# ============================================================
MR_RSI_PERIOD = 14
MR_RSI_OVERSOLD = 30
MR_RSI_OVERBOUGHT = 70
MR_BB_PERIOD = 20
MR_BB_STD = 2.0
MR_SL_ATR_MULT = 1.2
MR_MIN_RR = 1.5
MR_TIME_EXIT_BARS = 20      # Bars before forced exit

# ============================================================
# MODULE 3 — High Volatility
# ============================================================
HV_BAR_RANGE_MULT = 2.0     # Bar range > 2× avg of 20 bars
HV_BODY_RATIO = 0.6         # Body > 60% of total range
HV_ATR_EXPANSION = 0.2      # ATR > previous by 20%
HV_SL_ATR_MULT = 2.0
HV_MIN_RR = 1.5
HV_RISK_REDUCTION = 0.5     # 50% of base risk

# ============================================================
# EQUITY CURVE CONTROL (Layer D)
# ============================================================
EQUITY_SMA_PERIOD = 20
EQUITY_DRAWDOWN_REDUCTION = 0.5
SHARPE_DEVIATION_DAYS = 15   # Alert after N days of deviation
SHARPE_SHUTDOWN_DAYS = 30    # Shutdown after N days

# ============================================================
# EXECUTION (Layer E)
# ============================================================
PENDING_ORDER_EXPIRY_HOURS = 4
MAX_SLIPPAGE_TOLERANCE_PIPS = 1.0
MAX_PENDING_ORDERS_PER_PAIR = 2

# ============================================================
# SESSION FILTERS (All UTC)
# ============================================================
SESSIONS = {
    "london": {"start": 7, "end": 16},        # 07:00-16:00 UTC
    "ny_overlap": {"start": 12, "end": 16},    # 12:00-16:00 UTC
    "asian": {"start": 0, "end": 7},           # 00:00-07:00 UTC
}

NO_TRADE_BEFORE_CLOSE_MINUTES = 60
FRIDAY_CUTOFF_HOUR = 18      # No new trades after Friday 18:00 UTC
SUNDAY_NO_TRADE_BEFORE = 22  # No trades before Sunday 22:00 UTC

# ============================================================
# DATA COLLECTION
# ============================================================
MIN_DATA_YEARS = 3
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
CLEAN_DATA_DIR = os.path.join(DATA_DIR, "clean")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# ============================================================
# BACKTESTING
# ============================================================
TRAIN_RATIO = 0.70
WF_TRAIN_MONTHS = 6
WF_TEST_MONTHS = 2
MONTE_CARLO_ITERATIONS = 1000
MONTE_CARLO_DD_THRESHOLD = 0.20  # 95th pct DD < 20%

# Pass thresholds
MIN_PROFIT_FACTOR = 1.3
MAX_DRAWDOWN_PCT = 15.0
MIN_WIN_RATE = 0.40
MIN_SHARPE = 0.8
MIN_DSR = 0.95  # Deflated Sharpe Ratio

# ============================================================
# MONITORING & ALERTS
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("AMR_QTS_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("AMR_QTS_TELEGRAM_CHAT_ID", "")
