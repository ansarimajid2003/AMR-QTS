import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def analyze_csv(module):
    print(f"\n{'='*40}")
    print(f"ANALYZING: {module.upper()}")
    print(f"{'='*40}")
    
    file_path = PROJECT_ROOT / f"{module}_optimization_results.csv"
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
        
    df = pd.read_csv(file_path)
    
    # Filter for successful trials
    success_df = df[df['value'] > 0.0]
    
    if len(success_df) == 0:
        print("NO SUCCESSFUL TRIALS (value > 0.0) FOUND.")
        print("This means the constraints (WinRate > 40%, Sharpe > 0.5, PF > 1.0) were too strict for the searched parameter bounds.")
        
        print("\nTop 5 trials with parameters nearest to passing:")
        # We can't see the underlying metrics since value is 0.0
        # Just print 5 random sets from the search history
        pd.set_option('display.max_columns', None)
        param_cols = [c for c in df.columns if c.startswith('params_')]
        print(df[param_cols].head())
        
    else:
        print(f"Found {len(success_df)} successful parameter sets.")
        print("\nTop 5 Best Sets:")
        
        # Sort by value descending
        top5 = success_df.sort_values('value', ascending=False).head(5)
        
        for idx, row in top5.iterrows():
            print(f"\nRank {idx} (Score: {row['value']:.4f})")
            for col in df.columns:
                if col.startswith('params_'):
                    print(f"  {col.replace('params_', '')}: {row[col]:.4f}")

if __name__ == "__main__":
    analyze_csv("trend")
    analyze_csv("meanreversion")
    analyze_csv("highvol")
