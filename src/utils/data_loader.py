import os
import pandas as pd
from config.settings import CLEAN_DATA_DIR
from src.regime.regime_detector import Regime

def load_train_data(symbol="EURUSD"):
    """
    Load the _train.csv versions of the 15m entry data, H1 regime cache, and H4 structure cache.
    Ensures that test data is never used during parameter testing or optimization.
    """
    print(f"Loading {symbol} training data...")
    
    entry_file = os.path.join(CLEAN_DATA_DIR, f"{symbol}_15m_train.csv")
    h1_file = os.path.join(CLEAN_DATA_DIR, "cache", f"{symbol}_h1_regime_train.csv")
    h4_file = os.path.join(CLEAN_DATA_DIR, "cache", f"{symbol}_h4_structure_train.csv")
    
    if not all(os.path.exists(f) for f in [entry_file, h1_file, h4_file]):
        raise FileNotFoundError(
            f"Missing train data files in {CLEAN_DATA_DIR}. "
            "Make sure the _train.csv files have been generated."
        )
        
    entry_df = pd.read_csv(entry_file, index_col=0, parse_dates=True)
    h1_regime = pd.read_csv(h1_file, index_col=0, parse_dates=True)
    h4_structure = pd.read_csv(h4_file, index_col=0, parse_dates=True)
    
    # Convert regime string values back to Enum objects (as required by the backtester internals)
    h1_regime['regime'] = h1_regime['regime'].apply(
        lambda x: Regime[x] if isinstance(x, str) and x in Regime.__members__ else x
    )
    
    # H4 structure logic expects a pandas Series
    h4_structure_series = h4_structure['structure']
    
    print(f"  Loaded {len(entry_df):,} 15m bars.")
    print(f"  Loaded {len(h1_regime):,} 1h bars.")
    print(f"  Loaded {len(h4_structure):,} 4h bars.")
    return entry_df, h1_regime, h4_structure_series

def load_test_data(symbol="EURUSD"):
    """
    Load the _test.csv versions. Useful only for final out-of-sample forward walks.
    """
    print(f"Loading {symbol} TEST data (OUT OF SAMPLE)...")
    
    entry_file = os.path.join(CLEAN_DATA_DIR, f"{symbol}_15m_test.csv")
    h1_file = os.path.join(CLEAN_DATA_DIR, "cache", f"{symbol}_h1_regime_test.csv")
    h4_file = os.path.join(CLEAN_DATA_DIR, "cache", f"{symbol}_h4_structure_test.csv")
    
    if not all(os.path.exists(f) for f in [entry_file, h1_file, h4_file]):
        raise FileNotFoundError("Missing test data files.")
        
    entry_df = pd.read_csv(entry_file, index_col=0, parse_dates=True)
    h1_regime = pd.read_csv(h1_file, index_col=0, parse_dates=True)
    h4_structure = pd.read_csv(h4_file, index_col=0, parse_dates=True)
    
    h1_regime['regime'] = h1_regime['regime'].apply(
        lambda x: Regime[x] if isinstance(x, str) and x in Regime.__members__ else x
    )
    h4_structure_series = h4_structure['structure']
    
    return entry_df, h1_regime, h4_structure_series
