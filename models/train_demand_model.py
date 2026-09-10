"""
Standalone multi-model demand training script.
Evaluates XGBoost, LightGBM, RandomForest, GradientBoosting, and Ridge.
Ensures monotonicity constraints on price features.
Logs metrics and the best model to MLflow (DagsHub) and saves demand_model.pkl locally.
"""
import os
import shutil
import pickle
import json
from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
import xgboost as xgb
import lightgbm as lgb
import mlflow
import mlflow.sklearn
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "models" / "training_dataset.csv"
MODEL_PATH = ROOT / "models" / "demand_model.pkl"
COLS_PATH = ROOT / "models" / "feature_columns.pkl"

def check_monotonicity(model, expected_cols, base_check):
    prices = [10000, 15000, 20000, 25000]
    preds = []
    for p in prices:
        ctx = base_check.copy()
        ctx['current_price'] = p
        ctx['price_vs_competitor_ratio'] = p / ctx['competitor_avg_price']
        
        row_df = pd.DataFrame([ctx]).reindex(columns=expected_cols, fill_value=0)
        row_df = row_df.apply(pd.to_numeric, errors='coerce')
        pred = model.predict(row_df)[0]
        preds.append(pred)
    
    # Check that predictions are indeed non-increasing
    is_monotonic = all(preds[i] >= preds[i+1] for i in range(len(preds)-1))
    return is_monotonic, preds

def main():
    if not DATASET_PATH.exists():
        print(f"Error: Dataset {DATASET_PATH} not found.")
        return

    # MLflow tracking
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = "PIA-Dynamic-Pricing-MultiModel"
    mlflow.set_experiment(experiment_name)

    df = pd.read_csv(DATASET_PATH)
    target_col = "demand_ratio"
    y = df[target_col].fillna(0).clip(0.0, 1.0)
    
    feature_cols = [
        "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
        "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
        "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
        "competitor_data_is_real", "route", "flight_class"
    ]

    X = df[feature_cols].copy()
    X = pd.get_dummies(X, columns=["route", "flight_class"])

    expected_cols = [
        "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
        "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
        "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
        "competitor_data_is_real",
        "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
        "flight_class_Business", "flight_class_Economy"
    ]

    X = X.reindex(columns=expected_cols, fill_value=0)
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    constraints = {col: -1 if col in ["current_price", "price_vs_competitor_ratio"] else 0 for col in expected_cols}
    monotone_constraints = tuple(constraints[col] for col in expected_cols)

    models = {
        "XGBoost": xgb.XGBRegressor(max_depth=5, learning_rate=0.1, n_estimators=100, random_state=42, monotone_constraints=monotone_constraints),
        "LightGBM": lgb.LGBMRegressor(max_depth=5, learning_rate=0.1, n_estimators=100, random_state=42, monotone_constraints=monotone_constraints),
        "RandomForest": RandomForestRegressor(max_depth=5, n_estimators=100, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(max_depth=5, n_estimators=100, random_state=42),
        "Ridge": Ridge(alpha=1.0, random_state=42)
    }

    base_check = {
        'days_to_departure': 10, 'base_fare': 15000, 'time_of_day': 12, 'day_of_week': 2, 'is_weekend': 0, 'is_holiday_window': 0,
        'petrol_price': 280, 'diesel_price': 280, 'usd_to_pkr': 278, 'competitor_min_price': 12000, 'competitor_avg_price': 14000,
        'competitor_data_is_real': True, 'route_KHI-LHE': 1, 'flight_class_Economy': 1
    }

    results = []
    best_r2 = -float("inf")
    best_model = None
    best_model_name = None
    best_run_id = None

    for name, model in models.items():
        with mlflow.start_run(run_name=name) as run:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            is_monotonic, preds = check_monotonicity(model, expected_cols, base_check)

            # Log to MLflow
            mlflow.log_params({"model_type": name})
            try:
                # Log all hyperparameters for traceability
                mlflow.log_params(model.get_params())
            except Exception as e:
                print(f"Warning: Could not log params for {name}: {e}")
                
            mlflow.log_metrics({"rmse": rmse, "r2": r2, "is_monotonic": int(is_monotonic)})
            mlflow.sklearn.log_model(model, "model")

            results.append({
                "Model": name,
                "R2": r2,
                "RMSE": rmse,
                "Monotonic": is_monotonic,
                "Run_ID": run.info.run_id
            })

            # Update best model
            if is_monotonic and r2 > best_r2:
                best_r2 = r2
                best_model = model
                best_model_name = name
                best_run_id = run.info.run_id

    # Print comparison table
    print("\n" + "="*70)
    print(f"{'Model':<20} | {'R2':<10} | {'RMSE':<10} | {'Monotonic':<10}")
    print("-" * 70)
    for res in results:
        print(f"{res['Model']:<20} | {res['R2']:<10.4f} | {res['RMSE']:<10.4f} | {res['Monotonic']}")
    print("="*70 + "\n")

    if best_model is None:
        print("No model passed the monotonicity check!")
        return

    print(f"WINNER: {best_model_name} (Highest R2 among monotonic models: {best_r2:.4f})")
    print(f"MLFLOW RUN ID: {best_run_id}")
    
    # Save files locally
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(best_model, f)
    print(f"Saved model to {MODEL_PATH}")

    # Register model to DagsHub
    print("Registering model to DagsHub MLflow Registry...")
    local_model_dir = "local_temp_model"
    if os.path.exists(local_model_dir):
        shutil.rmtree(local_model_dir)
    
    from mlflow.models import infer_signature
    from mlflow.tracking import MlflowClient
    
    # Create model signature so DagsHub shows Inputs/Outputs
    signature = infer_signature(X_train, best_model.predict(X_train))
    
    mlflow.sklearn.save_model(best_model, local_model_dir, signature=signature)
    with mlflow.start_run(run_id=best_run_id):
        mlflow.log_artifacts(local_model_dir, artifact_path=best_model_name)
    
    # Register the model
    mv = mlflow.register_model(f"runs:/{best_run_id}/{best_model_name}", "pia-demand-model")
    
    # Assign 'champion' alias to the registered model
    client = MlflowClient()
    client.set_registered_model_alias("pia-demand-model", "champion", mv.version)
    
    print("Model registered successfully as 'pia-demand-model' with alias 'champion'.")
    
    # Save column features locally
    with open(COLS_PATH, "wb") as f:
        pickle.dump(expected_cols, f)
    
    # Verification
    print(f"\nSaved model to {MODEL_PATH}")
    # Load and print type
    with open(MODEL_PATH, "rb") as f:
        loaded_model = pickle.load(f)
    print(f"Verified saved model type: {type(loaded_model)}")

if __name__ == "__main__":
    main()
