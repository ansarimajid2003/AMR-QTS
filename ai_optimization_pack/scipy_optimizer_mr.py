import sys
import os
from pathlib import Path
import importlib
import numpy as np
import pandas as pd
import time
from scipy.optimize import differential_evolution

# Add the pack root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.strategy.modules import MeanReversionStrategy
from src.strategy.backtester import Backtester, analyze_trades
import config.settings as opt_settings
from run_optimization import load_data

# Data will be loaded in main process
ENTRY_DF = None
H1_REGIME = None
H4_STRUCTURE = None

def init_worker(entry_df, h1_regime, h4_structure):
    """Initialize worker process with shared data"""
    global ENTRY_DF, H1_REGIME, H4_STRUCTURE
    ENTRY_DF = entry_df
    H1_REGIME = h1_regime
    H4_STRUCTURE = h4_structure

class ScipyOptimizer:
    def __init__(self, maxiter=30, popsize=10, workers=12):
        """
        Initialize optimizer with runtime estimation.
        
        Args:
            maxiter: Maximum generations (default 30 for ~20-45min runtime)
            popsize: Population size multiplier (default 10)
            workers: Number of parallel workers (default 12, max 12 for 16-core CPU)
        """
        self.maxiter = maxiter
        self.popsize = popsize
        self.workers = min(workers, 12)  # Cap at 12 cores
        self.iteration = 0
        self.best_scores = []
        self.start_time = None
        
    def objective(self, params):
        """
        The objective function called by differential_evolution.
        params is a numpy array of the 8 parameters we are optimizing.
        SciPy minimizes the function, so we return the negative of your score.
        """
        self.iteration += 1
        
        try:
            # Validate RSI constraint early
            if params[1] >= params[2] - 5:  # Need at least 5 point gap
                return 1000.0
            
            # 1. Map SciPy array 'params' back to settings.
            # We must cast the integer parameters explicitly.
            setattr(opt_settings, 'MR_RSI_PERIOD', int(round(params[0])))
            setattr(opt_settings, 'MR_RSI_OVERSOLD', int(round(params[1])))
            setattr(opt_settings, 'MR_RSI_OVERBOUGHT', int(round(params[2])))
            setattr(opt_settings, 'MR_BB_PERIOD', int(round(params[3])))
            
            setattr(opt_settings, 'MR_BB_STD', float(params[4]))
            setattr(opt_settings, 'MR_SL_ATR_MULT', float(params[5]))
            setattr(opt_settings, 'MR_MIN_RR', float(params[6]))
            
            setattr(opt_settings, 'MR_TIME_EXIT_BARS', int(round(params[7])))

            module = MeanReversionStrategy("EURUSD")

            # 2. Run Backtest
            bt = Backtester(
                spread_pips=0.2,
                slippage_max=0.3,
                use_trailing=True,
                check_regime_exit=True
            )
            
            signals = module.generate_signals(ENTRY_DF, H1_REGIME, H4_STRUCTURE)
            
            trades = []
            if signals:
                trades = bt.simulate_trades(signals, ENTRY_DF, H1_REGIME)
                
            if len(trades) == 0:
                # ZONE 1: Proximity Gradient (0.001 to 0.999)
                prox = 0.0
                prox += (opt_settings.MR_RSI_OVERSOLD - 10) / 35.0
                prox += (90 - opt_settings.MR_RSI_OVERBOUGHT) / 35.0
                prox += (4.0 - opt_settings.MR_BB_STD) / 2.5
                prox = prox / 3.0
                score = max(0.001, min(0.999, prox))
                return -score # Return NEGATIVE score for SciPy to minimize
                
            metrics = analyze_trades(trades, module.name)
            
            # ZONE 2: Profit Gradient (1.000+)
            profit_factor = metrics['profit_factor']
            win_rate = metrics['win_rate']
            sharpe = metrics['sharpe']
            total_pnl = metrics['total_pnl_pips']
            
            profit_factor = 0.0 if pd.isna(profit_factor) else min(5.0, max(0.0, profit_factor))
            sharpe = -1.0 if pd.isna(sharpe) else min(3.0, max(-3.0, sharpe))
            win_rate = 0.0 if pd.isna(win_rate) else min(1.0, max(0.0, win_rate))
                
            shifted_sharpe = sharpe + 3.0
            raw_score = (profit_factor * 2.0) + shifted_sharpe + (win_rate * 10.0) 
            
            penalty_multiplier = len(trades) / 10.0 if len(trades) < 10 else 1.0
            score = 1.0 + (raw_score * penalty_multiplier)
            
            if total_pnl <= 0.0:
                 score = 1.0 + (score * 0.01)
            
            # Check for invalid values
            if pd.isna(score) or np.isnan(score) or np.isinf(score):
                return 1000.0
            
            # Print progress periodically
            if self.iteration % 20 == 0:
                elapsed = time.time() - self.start_time if self.start_time else 0
                print(f"[Eval {self.iteration}] Score: {score:.4f}, Trades: {len(trades)}, "
                      f"PF: {profit_factor:.2f}, WR: {win_rate:.2%}, Elapsed: {elapsed/60:.1f}m")
            
            # SciPy minimizes, so we want to find the lowest possible negative score
            return -score
            
        except Exception as e:
            print(f"Trial {self.iteration} failed with exception: {e}")
            return 1000.0  # Large positive value = bad for minimization

    def estimate_runtime(self):
        """
        Run a quick test to estimate total runtime.
        """
        print(f"\n{'='*50}")
        print("Running runtime estimation...")
        print(f"{'='*50}\n")
        
        # Generate random test parameters within bounds
        test_params = np.array([
            np.random.uniform(5, 30),      # RSI_PERIOD
            np.random.uniform(10, 45),     # RSI_OVERSOLD
            np.random.uniform(55, 90),     # RSI_OVERBOUGHT
            np.random.uniform(10, 50),     # BB_PERIOD
            np.random.uniform(1.5, 4.0),   # BB_STD
            np.random.uniform(0.5, 3.0),   # SL_ATR_MULT
            np.random.uniform(0.5, 3.0),   # MIN_RR
            np.random.uniform(4, 96)       # TIME_EXIT_BARS
        ])
        
        # Time 3 evaluations and average
        times = []
        for i in range(3):
            start = time.time()
            self.objective(test_params)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  Test run {i+1}/3: {elapsed:.2f}s")
        
        avg_time = np.mean(times)
        
        # Estimate total evaluations (conservative estimate)
        estimated_evals = self.maxiter * self.popsize * 8 * 0.3  # DE is more efficient
        
        # Estimate with parallelization
        estimated_total_seconds = (estimated_evals * avg_time) / self.workers
        estimated_minutes = estimated_total_seconds / 60
        estimated_hours = estimated_minutes / 60
        
        print(f"\n{'='*50}")
        print("Runtime Estimation:")
        print(f"  Avg time per evaluation: {avg_time:.2f}s")
        print(f"  Estimated total evaluations: ~{int(estimated_evals)}")
        print(f"  Using {self.workers} parallel workers")
        print(f"  Estimated total runtime: {estimated_minutes:.1f} minutes ({estimated_hours:.2f} hours)")
        print(f"{'='*50}\n")
        
        # Ask user confirmation
        response = input("Continue with optimization? (y/n): ").strip().lower()
        return response == 'y'

    def optimize(self, estimate_first=True):
        """
        Run the optimization with optional runtime estimation.
        
        Args:
            estimate_first: If True, runs estimation before optimization
        """
        # Runtime estimation
        if estimate_first:
            if not self.estimate_runtime():
                print("Optimization cancelled by user.")
                return None, None
        
        print(f"\n{'='*50}")
        print("Starting SciPy Differential Evolution for: MEANREVERSION")
        print(f"Configuration: maxiter={self.maxiter}, popsize={self.popsize}, workers={self.workers}")
        print(f"{'='*50}\n")
        
        self.start_time = time.time()
        self.iteration = 0  # Reset counter after estimation
        
        # Define the parameter bounds matching your Optuna space
        bounds = [
            (5, 30),     # MR_RSI_PERIOD
            (10, 45),    # MR_RSI_OVERSOLD
            (55, 90),    # MR_RSI_OVERBOUGHT
            (10, 50),    # MR_BB_PERIOD
            (1.5, 4.0),  # MR_BB_STD
            (0.5, 3.0),  # MR_SL_ATR_MULT
            (0.5, 3.0),  # MR_MIN_RR
            (4, 96)      # MR_TIME_EXIT_BARS
        ]
        
        # Constraint function to ensure RSI_OVERSOLD < RSI_OVERBOUGHT
        def rsi_constraint(params):
            """Ensure oversold < overbought with at least 10 point gap"""
            return params[2] - params[1] - 10  # Returns positive if valid
        
        
        # In single core, initialize the data globally for the main process
        init_worker(ENTRY_DF, H1_REGIME, H4_STRUCTURE)

        # Run differential evolution
        result = differential_evolution(
            func=self.objective,
            bounds=bounds,
            strategy='best1bin', 
            maxiter=self.maxiter,
            popsize=self.popsize,
            mutation=(0.5, 1.0),
            recombination=0.7,
            workers=1,  # Single core
            updating='deferred',
            seed=42,  # For reproducibility
            polish=True,  # Refine solution at the end
            disp=True,
            atol=0.01,  # Absolute tolerance for convergence
            tol=0.01    # Relative tolerance for convergence
        )
        
        total_time = time.time() - self.start_time
        
        print(f"\n{'='*50}")
        print("Optimization Complete for MEANREVERSION!")
        print(f"Total Runtime: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
        print(f"Total Function Evaluations: {result.nfev}")
        print(f"Evaluations per minute: {result.nfev / (total_time/60):.1f}")
        # We invert the returned function value back to positive to read the true "Score"
        print(f"Best Trial Value (Score): {-result.fun:.4f}")
        print(f"Optimization Status: {'Success' if result.success else 'Failed'}")
        print(f"Message: {result.message}")
        print("\nBest Parameters Found:")
        
        # Map back integer bounds for readability
        best_params = {
            "MR_RSI_PERIOD": int(round(result.x[0])),
            "MR_RSI_OVERSOLD": int(round(result.x[1])),
            "MR_RSI_OVERBOUGHT": int(round(result.x[2])),
            "MR_BB_PERIOD": int(round(result.x[3])),
            "MR_BB_STD": round(result.x[4], 4),
            "MR_SL_ATR_MULT": round(result.x[5], 4),
            "MR_MIN_RR": round(result.x[6], 4),
            "MR_TIME_EXIT_BARS": int(round(result.x[7]))
        }
        
        for key, value in best_params.items():
            print(f"  {key}: {value}")
        print(f"{'='*50}\n")
        
        # Verify the constraint is satisfied
        if best_params["MR_RSI_OVERSOLD"] >= best_params["MR_RSI_OVERBOUGHT"]:
            print("⚠️  WARNING: Best parameters violate RSI constraint!")
        else:
            print("✓ RSI constraint satisfied")
        
        # Save results to file
        self._save_results(best_params, result, total_time)
        
        return result, best_params
    
    def _save_results(self, best_params, result, total_time):
        """Save optimization results to a file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scipy_optimization_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("="*50 + "\n")
            f.write("SciPy Differential Evolution Results\n")
            f.write("="*50 + "\n\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Runtime: {total_time/60:.1f} minutes\n")
            f.write(f"Total Evaluations: {result.nfev}\n")
            f.write(f"Best Score: {-result.fun:.4f}\n")
            f.write(f"Success: {result.success}\n")
            f.write(f"Message: {result.message}\n\n")
            f.write("Best Parameters:\n")
            f.write("-"*50 + "\n")
            for key, value in best_params.items():
                f.write(f"{key}: {value}\n")
        
        print(f"\n✓ Results saved to: {filename}")

if __name__ == "__main__":
    # Load data ONLY in main process (not in workers)
    print("Loading data for SciPy optimization...")
    ENTRY_DF, H1_REGIME, H4_STRUCTURE = load_data()
    
    # Quick run (~20-40 minutes)
    optimizer = ScipyOptimizer(maxiter=30, popsize=10, workers=12)
    
    # For more thorough optimization (~45-90 minutes), use:
    # optimizer = ScipyOptimizer(maxiter=50, popsize=12, workers=12)
    
    # For fast testing (~10-15 minutes), use:
    # optimizer = ScipyOptimizer(maxiter=15, popsize=8, workers=12)
    
    result, best_params = optimizer.optimize(estimate_first=False)