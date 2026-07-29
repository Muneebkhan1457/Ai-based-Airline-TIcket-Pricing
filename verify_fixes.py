import pandas as pd
import numpy as np
import subprocess
import sys

# Paths
TRAINING_CSV = "models/training_dataset.csv"

def main():
    # Load dataset
    df = pd.read_csv(TRAINING_CSV)

    # 1. Price‑demand correlation (Pearson)
    corr = df["current_price"].corr(df["demand_ratio"]).round(4)

    # 2. Competitor data coverage (% rows with real data)
    coverage = (df["competitor_data_is_real"].mean() * 100).round(2)

    # 3. Macro‑signal variability (std dev)
    macro_std = df[["petrol_price", "diesel_price", "usd_to_pkr"]].std().round(2).to_dict()

    # 4. Holiday‑window capture (% rows flagged)
    holiday_pct = (df["is_holiday_window"].mean() * 100).round(2)

    # 5. CSV shape
    rows, cols = df.shape

    # Print results
    print("=== Verification Report ===")
    print(f"Price-Demand Correlation: {corr}")
    print(f"Competitor Data Coverage (%): {coverage}")
    print(f"Macro Signal Std Dev: {macro_std}")
    print(f"Holiday Window %: {holiday_pct}")
    print(f"CSV Shape: {rows} rows × {cols} cols")

    # Run pytest and capture result
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "Data_load/tests"], capture_output=True, text=True, check=False)
        print("\n--- Pytest Output ---")
        print(result.stdout)
    except Exception as e:
        print("Failed to run pytest:", e)

    # Run DB verification script (verify_db.py) and capture output
    try:
        result_db = subprocess.run([sys.executable, "Data_load/verify_db.py"], capture_output=True, text=True, check=False)
        print("\n--- DB Verification Output ---")
        print(result_db.stdout)
    except Exception as e:
        print("Failed to run DB verification:", e)

    # Folder tree (PowerShell Get-ChildItem -Recurse)
    try:
        result_tree = subprocess.run(["powershell", "-Command", "Get-ChildItem -Recurse | ForEach-Object { $_.FullName }"], capture_output=True, text=True, check=False)
        print("\n--- Folder Tree ---")
        print(result_tree.stdout)
    except Exception as e:
        print("Failed to list folder tree:", e)

if __name__ == "__main__":
    main()
