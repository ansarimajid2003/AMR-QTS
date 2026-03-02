# AMR-QTS AI Optimization Pack

You have been provided with a self-contained optimization environment for the AMR-QTS Quantitative Trading System.
Your objective is to optimize the hyperparameters of three distinct trading modules to improve their profitability, expectancy, and win rate.

## Optimization Strategy (Optuna Bayesian Search)
Instead of manually guessing parameters or running brute-force grid searches, you must use the included Optuna optimizer script. It will intelligently find the best parameters in a fraction of the time.

## Files In This Pack
- `config/settings.py` -> The parameter source of truth. Optuna will dynamically override these during its search.
- `run_optimization.py` -> The standard run script for evaluating the current hardcoded system settings.
- `optuna_optimizer.py` -> **EXECUTE THIS SCRIPT FIRST** to perform intelligent parameter sweeps. Optuna uses Tree-structured Parzen Estimator (TPE) to find winning combinations.
- `src/strategy/modules.py` -> The strategy logic behind signals.
- `src/strategy/backtester.py` -> The event-driven trade simulator.
- `data/` -> Historical 15m price data and pre-computed AI regime states in CSV format.

## Your Workflow
1. **Analyze:** Look at `src/strategy/modules.py` to see the logic of the three modules: `TrendStrategy`, `MeanReversionStrategy`, `HighVolStrategy`.
2. **Setup Optuna:** Open `optuna_optimizer.py` and modify the parameter search bounds within the `Optimizer.objective` method (e.g., widening the RSI search space, or tightening the SL range).
3. **Execute Search:** Run the optimizer from your terminal:
   - `python optuna_optimizer.py --module trend --trials 150`
   - `python optuna_optimizer.py --module meanreversion --trials 150`
   - `python optuna_optimizer.py --module highvol --trials 150`
4. **Apply Results:** The script will output the "Best Parameters Found". Take these values and permanently update `config/settings.py`.
5. **Verify:** Run the standard `python run_optimization.py` to confirm the total combined system performance using your newly discovered parameters.

Your goal is perfectly optimized parameters that pass:
- Profit Factor > 1.3
- Win Rate > 40%
- Sharpe > 0.8
- Expectancy > 0 pips/trade

Good luck!
