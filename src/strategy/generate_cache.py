import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CLEAN_DATA_DIR, MODELS_DIR, TRAIN_RATIO
from src.regime.regime_detector import HMMRegimeDetector, RegimeFeatureEngine, Regime
from src.strategy.modules import detect_h4_structure

def generate_cache(symbol: str = "EURUSD"):
    print(f"Generating regime detection cache for {symbol}...")
    
    # 1. Load data
    data = {}
    for tf in ['15m', '1h', '4h', '1d']:
        path = os.path.join(CLEAN_DATA_DIR, f"{symbol}_{tf}.parquet")
        if os.path.exists(path):
            data[tf] = pd.read_parquet(path)
        else:
            print(f"Missing {tf} data!")
            return

    entry_df = data['15m']
    h1_df = data['1h']
    h4_df = data['4h']

    # 2. Get train data
    split_idx = int(len(entry_df) * TRAIN_RATIO)
    train_entry = entry_df.iloc[:split_idx]
    
    # Trim H1 and H4 data to align with train end roughly for analysis, 
    # but the backtester uses the full H1/H4 index up to the split anyway
    
    # 3. Load HMM model
    model_path = os.path.join(MODELS_DIR, f"hmm_{symbol.lower()}.pkl")
    detector = HMMRegimeDetector.load(model_path)
    
    dxy_path = os.path.join(CLEAN_DATA_DIR, "DXY_1d.parquet")
    vix_path = os.path.join(CLEAN_DATA_DIR, "VIX_1d.parquet")
    dxy = pd.read_parquet(dxy_path) if os.path.exists(dxy_path) else None
    vix = pd.read_parquet(vix_path) if os.path.exists(vix_path) else None

    # Compute regime features for H1
    print("Computing H1 regimes...")
    raw_feat = detector.feature_engine.compute_raw_features(h1_df, dxy, vix)
    norm_feat = detector.feature_engine.normalize(raw_feat)
    h1_regime = detector.predict(norm_feat)
    
    # Compute structure for H4
    print("Computing H4 structure...")
    h4_structure = detect_h4_structure(h4_df)
    
    # 4. Save to CSV files
    out_dir = os.path.join(CLEAN_DATA_DIR, "cache")
    os.makedirs(out_dir, exist_ok=True)
    
    h1_out = os.path.join(out_dir, f"{symbol}_h1_regime.csv")
    h4_out = os.path.join(out_dir, f"{symbol}_h4_structure.csv")
    
    # Note: h1_regime contains Enum values in 'regime' column, need to cast to str
    h1_save = h1_regime.copy()
    h1_save['regime'] = h1_save['regime'].apply(lambda x: x.name if isinstance(x, Regime) else Regime(x).name)
    
    h1_save.to_csv(h1_out)
    h4_structure.to_frame('structure').to_csv(h4_out)
    
    print(f"Saved {len(h1_save)} h1 records to {h1_out}")
    print(f"Saved {len(h4_structure)} h4 records to {h4_out}")

if __name__ == "__main__":
    generate_cache("EURUSD")
