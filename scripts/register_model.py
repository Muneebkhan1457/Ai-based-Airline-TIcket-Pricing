"""
One-time script: logs the winning LightGBM model to DagsHub MLflow with the
correct metrics and registers it in the Model Registry as 'pia-demand-model'.

Run from the project root:
    python scripts/register_model.py
"""
import os
import sys

# Reconfigure stdout/stderr to UTF-8 on Windows so MLflow's emoji output
# (e.g. the 🏃 run link) does not crash with a UnicodeEncodeError on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import mlflow
import mlflow.sklearn
import mlflow.lightgbm
from mlflow.tracking import MlflowClient

# ── Config ──────────────────────────────────────────────────────────────────
TRACKING_URI   = os.environ["MLFLOW_TRACKING_URI"]
EXPERIMENT     = "PIA-Dynamic-Pricing-MultiModel"
MODEL_NAME     = "pia-demand-model"
PKL_PATH       = ROOT / "models" / "demand_model.pkl"
FEAT_PATH      = ROOT / "models" / "feature_columns.pkl"

# Known metrics for the winning LightGBM run
METRICS = {
    "r2":            0.4801,
    "rmse":          0.1444,
    "is_monotonic":  1.0,
}
PARAMS = {
    "model_type":    "LGBMRegressor",
    "n_estimators":  "500",
    "learning_rate": "0.05",
    "num_leaves":    "31",
}
TAGS = {
    "winning_model": "true",
    "notes": "LightGBM winner from multi-model comparison; registered via scripts/register_model.py",
}
# ────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Tracking URI : {TRACKING_URI}")
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient()

    # 1. Ensure experiment exists
    exp = client.get_experiment_by_name(EXPERIMENT)
    if exp is None:
        exp_id = client.create_experiment(EXPERIMENT)
        print(f"Created experiment '{EXPERIMENT}' (id={exp_id})")
    else:
        exp_id = exp.experiment_id
        print(f"Using experiment '{EXPERIMENT}' (id={exp_id})")

    # 2. Load the pkl
    print(f"Loading model from: {PKL_PATH}")
    with open(PKL_PATH, "rb") as f:
        model = pickle.load(f)
    print(f"Model type: {type(model).__name__}")

    # 3. Log run with correct metrics + register
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="lgbm_winner_registered") as run:
        mlflow.log_params(PARAMS)
        mlflow.log_metrics(METRICS)
        for k, v in TAGS.items():
            mlflow.set_tag(k, v)

        # Log the model artifact under the run
        mlflow.lightgbm.log_model(
            lgb_model=model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        run_id = run.info.run_id
        print(f"Run logged: {run_id}")

    # 4. Confirm registration
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    if versions:
        latest = max(versions, key=lambda v: int(v.version))
        print(f"\n✅ Model registered: {MODEL_NAME} v{latest.version}")
        print(f"   Stage  : {latest.current_stage}")
        print(f"   Source : {latest.source[:80]}")
    else:
        print("❌ Registration may have failed — no versions found after logging.")

    print("\nDone. Metrics logged:")
    for k, v in METRICS.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
