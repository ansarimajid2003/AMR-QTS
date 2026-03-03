import sys
import os
from pathlib import Path
import copy
import optuna
import pandas as pd

# Add the pack root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.strategy.modules import TrendStrategy, MeanReversionStrategy, HighVolStrategy
from src.strategy.backtester import Backtester, analyze_trades
import config.settings as opt_settings

# Import existing data loading
from run_optimization import load_data

print("Loading data for optimization...")
ENTRY_DF, H1_REGIME, H4_STRUCTURE = load_data()

class Optimizer:
    def __init__(self, module_name, n_trials=100, n_jobs=8):
        self.module_name = module_name
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        
    def objective(self, trial):
        try:
            # We need a clean slate of settings for each trial
            import importlib
            importlib.reload(opt_settings)
            
            # Select module and inject Optuna parameters into settings
            if self.module_name.lower() == "trend":
                module = TrendStrategy("EURUSD")
                
                # --- WIDENED SEARCH BOUNDS FOR TREND ---
                opt_settings.TREND_BREAKOUT_BARS = trial.suggest_int("TREND_BREAKOUT_BARS", 5, 100)
                opt_settings.TREND_ATR_EXPANSION = trial.suggest_float("TREND_ATR_EXPANSION", 0.5, 4.0, step=0.01)
                opt_settings.TREND_SL_ATR_MULT = trial.suggest_float("TREND_SL_ATR_MULT", 1.0, 4.0, step=0.01)
                opt_settings.TREND_RR_PRIMARY = trial.suggest_float("TREND_RR_PRIMARY", 1.0, 5.0, step=0.01)
                opt_settings.TREND_RR_TRAIL_ACTIVATION = trial.suggest_float("TREND_RR_TRAIL_ACTIVATION", 0.5, 3.0, step=0.01)
                
                # Dynamic Logic
                opt_settings.TREND_USE_EMA_FILTER = trial.suggest_categorical("TREND_USE_EMA_FILTER", [True, False])
                opt_settings.TREND_RSI_LONG_MIN = trial.suggest_int("TREND_RSI_LONG_MIN", 30, 60)
                opt_settings.TREND_RSI_LONG_MAX = trial.suggest_int("TREND_RSI_LONG_MAX", 65, 95)
                opt_settings.TREND_RSI_SHORT_MIN = trial.suggest_int("TREND_RSI_SHORT_MIN", 5, 35)
                opt_settings.TREND_RSI_SHORT_MAX = trial.suggest_int("TREND_RSI_SHORT_MAX", 40, 70)
                
            elif self.module_name.lower() == "meanreversion":
                module = MeanReversionStrategy("EURUSD")
                
                # --- WIDENED SEARCH BOUNDS FOR MEAN REVERSION ---
                opt_settings.MR_RSI_PERIOD = trial.suggest_int("MR_RSI_PERIOD", 5, 30)
                opt_settings.MR_RSI_OVERSOLD = trial.suggest_int("MR_RSI_OVERSOLD", 10, 45)
                opt_settings.MR_RSI_OVERBOUGHT = trial.suggest_int("MR_RSI_OVERBOUGHT", 55, 90)
                opt_settings.MR_BB_PERIOD = trial.suggest_int("MR_BB_PERIOD", 10, 50)
                opt_settings.MR_BB_STD = trial.suggest_float("MR_BB_STD", 1.5, 4.0, step=0.01)
                opt_settings.MR_SL_ATR_MULT = trial.suggest_float("MR_SL_ATR_MULT", 0.5, 3.0, step=0.01)
                opt_settings.MR_MIN_RR = trial.suggest_float("MR_MIN_RR", 0.5, 3.0, step=0.01)
                opt_settings.MR_TIME_EXIT_BARS = trial.suggest_int("MR_TIME_EXIT_BARS", 4, 96) # 1 hour to 24 hours
                
            elif self.module_name.lower() == "highvol":
                module = HighVolStrategy("EURUSD")
                
                # --- WIDENED SEARCH BOUNDS FOR HIGH VOL ---
                opt_settings.HV_BAR_RANGE_MULT = trial.suggest_float("HV_BAR_RANGE_MULT", 1.1, 5.0, step=0.01)
                opt_settings.HV_BODY_RATIO = trial.suggest_float("HV_BODY_RATIO", 0.3, 0.95, step=0.01)
                opt_settings.HV_ATR_EXPANSION = trial.suggest_float("HV_ATR_EXPANSION", 0.05, 2.0, step=0.01)
                opt_settings.HV_SL_ATR_MULT = trial.suggest_float("HV_SL_ATR_MULT", 1.0, 4.0, step=0.01)
                opt_settings.HV_MIN_RR = trial.suggest_float("HV_MIN_RR", 1.0, 4.0, step=0.01)
                opt_settings.HV_RISK_REDUCTION = trial.suggest_float("HV_RISK_REDUCTION", 0.1, 1.0, step=0.01)
                
            else:
                raise ValueError(f"Unknown module {self.module_name}")

            # 2. Run Backtest
            bt = Backtester(
                spread_pips=0.2,
                slippage_max=0.3,
                use_trailing=True,
                check_regime_exit=True
            )
            
            # It's critical the module uses the reloaded opt_settings
            signals = module.generate_signals(ENTRY_DF, H1_REGIME, H4_STRUCTURE)
            
            trades = []
            if signals:
                trades = bt.simulate_trades(signals, ENTRY_DF, H1_REGIME)
                
            if len(trades) == 0:
                # ZONE 1: Proximity Gradient (0.001 to 0.999)
                # Rewards the AI for picking mathematically more lenient parameters to encourage a trade
                prox = 0.0
                if self.module_name.lower() == "trend":
                    prox += (100 - opt_settings.TREND_BREAKOUT_BARS) / 95.0
                    prox += (4.0 - opt_settings.TREND_ATR_EXPANSION) / 3.5
                    prox += (opt_settings.TREND_RSI_LONG_MAX - opt_settings.TREND_RSI_LONG_MIN) / 65.0
                    prox += (opt_settings.TREND_RSI_SHORT_MAX - opt_settings.TREND_RSI_SHORT_MIN) / 65.0
                    prox += 1.0 if not opt_settings.TREND_USE_EMA_FILTER else 0.0
                    prox = prox / 5.0
                elif self.module_name.lower() == "meanreversion":
                    prox += (opt_settings.MR_RSI_OVERSOLD - 10) / 35.0
                    prox += (90 - opt_settings.MR_RSI_OVERBOUGHT) / 35.0
                    prox += (4.0 - opt_settings.MR_BB_STD) / 2.5
                    prox = prox / 3.0
                elif self.module_name.lower() == "highvol":
                    prox += (5.0 - opt_settings.HV_BAR_RANGE_MULT) / 3.9
                    prox += (2.0 - opt_settings.HV_ATR_EXPANSION) / 1.95
                    prox += (0.95 - opt_settings.HV_BODY_RATIO) / 0.65
                    prox = prox / 3.0
                
                return max(0.001, min(0.999, prox))
                
            metrics = analyze_trades(trades, module.name)
            
            # ZONE 2: Profit Gradient (1.000+)
            profit_factor = metrics['profit_factor']
            win_rate = metrics['win_rate']
            sharpe = metrics['sharpe']
            total_pnl = metrics['total_pnl_pips']
            
            if pd.isna(profit_factor):
                profit_factor = 0.0
            profit_factor = min(5.0, max(0.0, profit_factor))
                
            if pd.isna(sharpe):
                sharpe = -1.0
            sharpe = min(3.0, max(-3.0, sharpe))
                
            if pd.isna(win_rate):
                win_rate = 0.0
            win_rate = min(1.0, max(0.0, win_rate))
                
            # Shift the score entirely into the positive domain
            shifted_sharpe = sharpe + 3.0 # Now 0.0 to 6.0
            
            # Base raw score (Strictly positive)
            raw_score = (profit_factor * 2.0) + shifted_sharpe + (win_rate * 10.0) 
            
            # Gently penalize under 10 trades per quarter to prevent 1-trade overfitting
            if len(trades) < 10:
                penalty_multiplier = len(trades) / 10.0
            else:
                penalty_multiplier = 1.0
                
            # Base 1.0 permanently outranks ANY 0-trade Proximity Score
            score = 1.0 + (raw_score * penalty_multiplier)
            
            # Heavy penalty if the strategy lost money
            if total_pnl <= 0.0:
                 score = 1.0 + (score * 0.01)
            
            if pd.isna(score):
                return 0.0
            
            return score
        except Exception as e:
            print(f"Trial failed with exception: {e}")
            return 0.0

    def optimize(self):
        print(f"\n{'='*50}")
        print(f"Starting Optuna Optimization for: {self.module_name.upper()}")
        print(f"Trials: {self.n_trials}")
        print(f"{'='*50}\n")
        
        # Enable basic logging to show progress every 10 runs
        optuna.logging.set_verbosity(optuna.logging.INFO)
        
        # Create Optuna study to maximize our fitness score
        study = optuna.create_study(direction="maximize")
        
        # Use joblib to parallelize optimization, which is much safer and faster on Windows
        import joblib
        with joblib.parallel_backend("loky", n_jobs=self.n_jobs):
            study.optimize(self.objective, n_trials=self.n_trials)
        
        print(f"\n{'='*50}")
        print(f"Optimization Complete for {self.module_name.upper()}!")
        print(f"Best Trial Value (Score): {study.best_value:.4f}")
        print("Best Parameters Found:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value}")
        print(f"{'='*50}\n")
        
        # Save results to a CSV
        results_df = study.trials_dataframe()
        results_path = os.path.join(PROJECT_ROOT, f"{self.module_name.lower()}_optimization_results.csv")
        results_df.to_csv(results_path)
        print(f"Full trial results saved to: {results_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Optuna hyperparameter optimizer for AMR-QTS modules.')
    parser.add_argument('--module', type=str, required=True, choices=['trend', 'meanreversion', 'highvol'], 
                        help='Which module to optimize.')
    parser.add_argument('--trials', type=int, default=100, help='Number of optuna trials to run.')
    parser.add_argument('--cores', type=int, default=8, help='Number of CPU cores to use.')
    args = parser.parse_args()
    
    optimizer = Optimizer(args.module, args.trials, args.cores)
    optimizer.optimize()
