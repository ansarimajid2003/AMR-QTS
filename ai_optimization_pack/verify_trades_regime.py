import sys
import os
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_optimization import load_data
from src.strategy.modules import MeanReversionStrategy

def verify():
    entry_df, h1_regime, h4_structure = load_data()
    print("\nScanning for Mean Reversion trades...")
    
    mod = MeanReversionStrategy("EURUSD")
    signals = mod.generate_signals(entry_df, h1_regime, h4_structure)
    
    if not signals:
        print("No signals found.")
        return
        
    print(f"\n=========================================")
    print(f"MEAN REVERSION TRADE REGIME BREAKDOWN")
    print(f"=========================================")
    print(f"Total Signals Generated: {len(signals)}")
    
    regime_counts = {}
    for sig in signals:
        # sig.regime is an Enum
        r = sig.regime.name
        regime_counts[r] = regime_counts.get(r, 0) + 1
        
    for r, count in regime_counts.items():
        print(f"  -> Regime {r}: {count} trades ({count/len(signals)*100:.1f}%)")
        
    print("\nVerification: If the number above is 100.0% RANGING, the HMM gate is working flawlessly.")

if __name__ == "__main__":
    verify()
