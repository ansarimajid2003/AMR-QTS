import os
import re

MODULES_PATH = r"c:\Users\ansar\Documents\Adaptive Multi-Regime Quantitative Trading System (AMR-QTS)\src\strategy\modules.py"
BACKTESTER_PATH = r"c:\Users\ansar\Documents\Adaptive Multi-Regime Quantitative Trading System (AMR-QTS)\src\strategy\backtester.py"

# Variables to prefix with opt_settings.
vars_to_replace = [
    "TREND_BREAKOUT_BARS", "TREND_ATR_EXPANSION", "TREND_RSI_LONG_RANGE",
    "TREND_RSI_SHORT_RANGE", "TREND_SL_ATR_MULT", "TREND_RR_PRIMARY",
    "TREND_RR_TRAIL_ACTIVATION", "TREND_MFE_RETRACE_EXIT",
    "MR_RSI_PERIOD", "MR_RSI_OVERSOLD", "MR_RSI_OVERBOUGHT",
    "MR_BB_PERIOD", "MR_BB_STD", "MR_SL_ATR_MULT", "MR_MIN_RR", "MR_TIME_EXIT_BARS",
    "HV_BAR_RANGE_MULT", "HV_BODY_RATIO", "HV_ATR_EXPANSION",
    "HV_SL_ATR_MULT", "HV_MIN_RR", "HV_RISK_REDUCTION",
    "ADX_PERIOD", "ATR_PERIOD", "EMA_FAST", "EMA_SLOW", "EMA_PROXIMITY_THRESHOLD",
    "BASE_RISK_PCT", "MAX_SLIPPAGE_PIPS", "SPREAD_PIPS",
    "HMM_MIN_CONFIDENCE"
]

def refactor_file(filepath, import_lines_regex):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace the old import block with the new one
    content = re.sub(import_lines_regex, "import config.settings as opt_settings", content, count=1, flags=re.MULTILINE|re.DOTALL)
    
    # Prefix variables
    for var in set(vars_to_replace):
        # Only replace word boundaries that aren't already prefixed with opt_settings.
        content = re.sub(r'(?<!opt_settings\.)\b{}\b'.format(var), f"opt_settings.{var}", content)
        
    with open(filepath, 'w') as f:
        f.write(content)

modules_import_regex = r"from config\.settings import \([^)]+\)"
refactor_file(MODULES_PATH, modules_import_regex)

backtester_import_regex = r"from config\.settings import \([^)]+\)"
refactor_file(BACKTESTER_PATH, backtester_import_regex)

print("Refactored modules.py and backtester.py")
