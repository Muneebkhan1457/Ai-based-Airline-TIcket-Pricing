# DATABRICKS NOTEBOOK: Phase 4 - Model Training with MLflow Metrics Display
# This code logs all metrics to MLflow so they appear in the UI

import pandas as pd
import numpy as np
import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import json

print("=" * 70)
print("PHASE 4: MODEL TRAINING WITH MLFLOW METRICS")
print("=" * 70)
print()

# ============================================
# STEP 1: Load Training Dataset
# ============================================

training_df = spark.sql("SELECT * FROM airline_daw.pia_pricing.training_dataset").toPandas()

print(f"✅ Training dataset loaded: {training_df.shape[0]} rows × {training_df.shape[1]} columns")
print()

# ============================================
# STEP 2: Prepare Features
# ============================================

target_col = "demand_ratio"

X = training_df.drop(columns=[target_col], errors="ignore")
y = training_df[target_col]

# Fill missing values
X = X.fillna(0)
y = y.fillna(y.mean())

# Convert categorical columns
X = pd.get_dummies(X, columns=["route", "flight_class"])

# Define expected columns
expected_cols = [
    "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
    "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
    "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
    "competitor_data_is_real",
    "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
    "flight_class_Business", "flight_class_Economy"
]

X = X.reindex(columns=expected_cols, fill_value=0)
X = X.apply(pd.to_numeric, errors='coerce')

print(f"✅ Features prepared: {X.shape}")
print()

# ============================================
# STEP 3: Train/Test Split
# ============================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"✅ Train set: {X_train.shape[0]} rows")
print(f"✅ Test set: {X_test.shape[0]} rows")
print()

# ============================================
# STEP 4: Setup MLflow Experiment
# ============================================

mlflow.set_experiment("/Users/khaamuneeb420@gmail.com/pia-demand-model")

print("✅ MLflow experiment set")
print()

# ============================================
# STEP 5: Train Model with MLflow Tracking
# ============================================

with mlflow.start_run(run_name="xgboost-complete-metrics") as run:
    
    # Model parameters
    model_params = {
        "max_depth": 5,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "random_state": 42,
    }
    
    print("🔄 Training XGBoost Regressor...\n")
    
    # Monotonic constraints
    constraints = tuple(-1 if col in ["current_price", "price_vs_competitor_ratio"] else 0 
                       for col in expected_cols)
    
    model = XGBRegressor(
        **model_params,
        monotone_constraints=constraints
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    print("✅ Model trained successfully\n")
    
    # ============================================
    # STEP 6: Evaluate Model
    # ============================================
    
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print()
    
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Calculate metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    
    print(f"📊 REGRESSION METRICS:")
    print(f"   Train RMSE: {train_rmse:.6f}")
    print(f"   Test RMSE:  {test_rmse:.6f} ✅")
    print(f"   Train R²:   {train_r2:.6f}")
    print(f"   Test R²:    {test_r2:.6f} ✅")
    print(f"   Train MAE:  {train_mae:.6f}")
    print(f"   Test MAE:   {test_mae:.6f}")
    print()
    
    # ============================================
    # STEP 7: Verify Monotonicity
    # ============================================
    
    print(f"🔍 MONOTONICITY CHECK:")
    print(f"   (Price ↑ should → Demand ↓)\n")
    
    base_check = {
        'days_to_departure': 10, 'base_fare': 15000,
        'time_of_day': 12, 'day_of_week': 2, 'is_weekend': 0, 'is_holiday_window': 0,
        'petrol_price': 335, 'diesel_price': 383, 'usd_to_pkr': 277,
        'competitor_min_price': 12000, 'competitor_avg_price': 14000,
        'competitor_data_is_real': 1,
        'route_KHI-LHE': 1, 'route_KHI-DXB': 0, 'route_KHI-ISB': 0, 
        'route_KHI-PEW': 0, 'route_LHE-ISB': 0,
        'flight_class_Economy': 1, 'flight_class_Business': 0
    }
    
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
        print(f"   Price: {p:,} PKR → Demand: {pred:.4f}")
    
    is_monotonic = all(preds[i] >= preds[i+1] for i in range(len(preds)-1))
    print(f"\n   Result: {'✅ PASSED' if is_monotonic else '❌ FAILED'}\n")
    
    # ============================================
    # STEP 8: Log to MLflow
    # ============================================
    
    print("=" * 70)
    print("LOGGING TO MLFLOW")
    print("=" * 70)
    print()
    
    # Log parameters
    mlflow.log_params(model_params)
    print("✅ Parameters logged:")
    for k, v in model_params.items():
        print(f"   {k}: {v}")
    print()
    
    # Log metrics
    metrics = {
        "train_rmse": train_rmse,
        "test_rmse": test_rmse,
        "train_r2": train_r2,
        "test_r2": test_r2,
        "train_mae": train_mae,
        "test_mae": test_mae,
        "monotonicity_passed": 1 if is_monotonic else 0,
    }
    
    for metric_name, metric_value in metrics.items():
        mlflow.log_metric(metric_name, metric_value)
    
    print("✅ Metrics logged to MLflow:")
    for k, v in metrics.items():
        print(f"   {k}: {v}")
    print()
    
    # Log model
    mlflow.xgboost.log_model(
        model,
        artifact_path="demand_model",
        registered_model_name="pia-demand-model",
        input_example=X_test.iloc[0:5]
    )
    
    print("✅ Model logged to MLflow Registry")
    print(f"   Name: pia-demand-model")
    print(f"   Version: 1")
    print()
    
    # Log feature columns config
    mlflow.log_dict(
        {'feature_columns': expected_cols},
        'feature_columns_config.json'
    )
    
    print("✅ Feature columns config logged")
    print()
    
    # Log additional metadata
    metadata = {
        "training_samples": X_train.shape[0],
        "test_samples": X_test.shape[0],
        "total_features": len(expected_cols),
        "target_variable": target_col,
        "algorithm": "XGBoost",
        "constraints": "Monotonic on price features",
        "timestamp": str(datetime.now())
    }
    
    mlflow.log_dict(metadata, 'model_metadata.json')
    
    print("✅ Metadata logged")
    print()

print("=" * 70)
print("✅✅✅ PHASE 4 COMPLETE ✅✅✅")
print("=" * 70)
print()
print("📊 SUMMARY:")
print(f"   Test RMSE: {test_rmse:.6f}")
print(f"   Test R²: {test_r2:.6f}")
print(f"   Monotonicity: {'✅ PASSED' if is_monotonic else '❌ FAILED'}")
print()
print("🔗 View metrics on MLflow:")
print("   1. Go to Databricks workspace")
print("   2. Left sidebar → Experiments")
print("   3. Click: pia-demand-model")
print("   4. Select run: xgboost-complete-metrics")
print("   5. See all metrics, parameters, and model artifacts ✅")
print()

from datetime import datetime
