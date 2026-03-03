import os
import glob
import pandas as pd
from pathlib import Path

def inspect_and_split():
    # Identify directories
    base_dirs = [
        "data/clean",
        "data/clean/cache",
        "ai_optimization_pack/data"
    ]
    
    csv_files = []
    for d in base_dirs:
        # Get all CSVs directly in the directory
        csvs = glob.glob(os.path.join(d, "*.csv"))
        # Filter out already split files and backtest results
        csvs = [f for f in csvs if not f.endswith("_train.csv") and not f.endswith("_test.csv") and "results" not in f]
        csv_files.extend(csvs)
        
    print(f"Found {len(csv_files)} target CSV files.")
    
    # Process files
    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                print(f"Skipping {file_path} - not a suitable time-series dataframe.")
                continue
                
            # Perform a 70/30 split chronologically based on number of rows
            split_idx = int(len(df) * 0.70)
            split_date = df.index[split_idx]
            
            # Create the train and test splits
            train_df = df.iloc[:split_idx]
            test_df = df.iloc[split_idx:]
            
            # Save the new files
            base, ext = os.path.splitext(file_path)
            train_path = f"{base}_train{ext}"
            test_path = f"{base}_test{ext}"
            
            train_df.to_csv(train_path)
            test_df.to_csv(test_path)
            
            print(f"Successfully split {file_path}:")
            print(f"  - Train: {len(train_df)} rows (End: {train_df.index[-1]})")
            print(f"  - Test:  {len(test_df)} rows (Start: {test_df.index[0]})")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    inspect_and_split()
