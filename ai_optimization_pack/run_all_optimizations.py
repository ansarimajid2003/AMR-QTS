import sys
import os
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent

def run_all():
    print("==================================================")
    print("AMR-QTS FULL PIPELINE OPTIMIZATION")
    print("==================================================\n")
    
    modules = ['trend', 'highvol']
    trials = 300 # Deep optimization run
    
    for mod in modules:
        print(f">>> Queuing Optimization for: {mod.upper()}")
        
    print(f"\nTotal Trials Scheduled: {len(modules) * trials}")
    print("Starting in 3 seconds...\n")
    
    import time
    time.sleep(3)
    
    for mod in modules:
        script_path = os.path.join(PROJECT_ROOT, "optuna_optimizer.py")
        cmd = [sys.executable, script_path, "--module", mod, "--trials", str(trials)]
        
        try:
            # We use subprocess.run so they execute sequentially, one after another
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Optimization for {mod} failed with code {e.returncode}.")
            sys.exit(1)
            
    print("\n==================================================")
    print("ALL OPTIMIZATIONS COMPLETE!")
    print("Check the generated .csv files in this directory for results.")
    print("==================================================\n")

if __name__ == "__main__":
    run_all()
