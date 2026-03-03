import os
import glob
import pandas as pd
from pathlib import Path

def get_base_name(file_path):
    # Extracts the symbol part before timeframe, e.g. "EURUSD" from "EURUSD_15m.csv"
    basename = os.path.basename(file_path)
    return basename.split("_")[0]

def inspect_and_split():
    base_dirs = [
        "data/clean",
        "data/clean/cache",
        "ai_optimization_pack/data"
    ]
    
    csv_files = []
    for d in base_dirs:
        csvs = glob.glob(os.path.join(d, "*.csv"))
        # Filter out already split files and backtest results
        csvs = [f for f in csvs if not f.endswith("_train.csv") and not f.endswith("_test.csv") and "results" not in f]
        csv_files.extend(csvs)
        
    print(f"Found {len(csv_files)} target CSV files.")
    
    # 1. First Pass: Find the 15m split dates for each symbol in data/clean
    # We will use this date to split all files for that symbol
    split_dates = {}
    
    # Look for the primary 15m files to determine split date
    for file_path in csv_files:
        if "15m" in file_path and ("data" + os.sep + "clean" in file_path or "data/clean" in file_path):
            symbol = get_base_name(file_path)
            # Only read once per symbol to find the master split date
            if symbol not in split_dates:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                split_idx = int(len(df) * 0.70)
                split_date = df.index[split_idx]
                split_dates[symbol] = split_date
                print(f"Master split date for {symbol} set to: {split_date}")
                
    # Fallback if no 15m file was found in data/clean (e.g. searching ai_optimization_pack)
    for file_path in csv_files:
        if "15m" in file_path:
            symbol = get_base_name(file_path)
            if symbol not in split_dates:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                split_idx = int(len(df) * 0.70)
                split_date = df.index[split_idx]
                split_dates[symbol] = split_date
                print(f"Fallback master split date for {symbol} set to: {split_date}")
    
    # 2. Second Pass: Apply to all files
    for file_path in csv_files:
        try:
            symbol = get_base_name(file_path)
            split_date = split_dates.get(symbol)
            
            if not split_date:
                print(f"Skipping {file_path} - could not determine a master split date for symbol {symbol}.")
                continue
                
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                print(f"Skipping {file_path} - not a suitable time-series dataframe.")
                continue
                
            # Perform chronological split based on the master split date
            train_df = df[df.index < split_date]
            test_df = df[df.index >= split_date]
            
            # Save the new files
            base, ext = os.path.splitext(file_path)
            train_path = f"{base}_train{ext}"
            test_path = f"{base}_test{ext}"
            
            train_df.to_csv(train_path)
            test_df.to_csv(test_path)
            
            print(f"Successfully split {file_path}:")
            if not train_df.empty:
                print(f"  - Train: {len(train_df)} rows (End:   {train_df.index[-1]})")
            if not test_df.empty:
                print(f"  - Test:  {len(test_df)} rows (Start: {test_df.index[0]})")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    inspect_and_split()
