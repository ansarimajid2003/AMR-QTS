import pandas as pd
import numpy as np
from pathlib import Path

# Load data similarly to how run_optimization does it
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

# Load the H1 features file which contains the regimes
h1_file = DATA_DIR / "EURUSD_h1_regime.csv"
if not h1_file.exists():
    print(f"Error: Could not find H1 features file at {h1_file}")
else:
    df = pd.read_csv(h1_file, index_col=0, parse_dates=True)
    
    # The dataframe is already cropped to the optimization window.
    # Let's count the occurrences of each regime
    if 'regime' in df.columns:
        counts = df['regime'].value_counts(normalize=True) * 100
        print("\n=========================================")
        print(f"REGIME DISTRIBUTION FOR OPTIMIZER")
        print("=========================================\n")
        print(f"Total H1 Bars Analyzed: {len(df)}")
        for regime, pct in counts.items():
            print(f"Regime {regime}: {pct:.2f}% of the time")
    else:
        print("hmm_regime column not found in H1 dataset.")
