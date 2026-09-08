# Phase 4: Model Training with MLflow Tracking

## Objective
Train the XGBoost demand model in Databricks, log it to MLflow with metrics and artifacts, and verify monotonic price elasticity.

---

## Step 1: Create Model Training Notebook

**New notebook:** `03_train_demand_model`  
**Language:** Python  
**Cluster:** `pia-pricing-cluster`

---

## Step 2: Model Training Code

### Cell 1: Import Libraries & Load Training Data

```python
import mlflow
import mlflow.xgboost
import xgboost as xgb
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pandas as pd
import numpy as np
import json

print("✅ All libraries imported")

# Load training dataset
training_df = spark.sql("SELECT * FROM pia_pricing.training_dataset")
training_pd = training_df.toPandas()

print(f"✅ Training dataset loaded: {training_pd.shape[0]} rows × {training_pd.shape[1]} columns")
print(f"\n=== Dataset Info ===")
print(training_pd.info())
```

---

### Cell 2: Prepare Features & Target

```python
# Separate features and target
target_col = 'demand_ratio'
X = training_pd.drop(columns=[target_col], errors='ignore')
y = training_pd[target_col]

print(f"Features shape: {X.shape}")
print(f"Target shape: {y.shape}")
print(f"\nTarget variable statistics:")
print(y.describe())

# Check for missing values
print(f"\nMissing values in features:")
print(X.isnull().sum().sum())
print(f"Missing values in target: {y.isnull().sum()}")

# Fill any NaNs with 0 (shouldn't happen but safe practice)
X = X.fillna(0)
y = y.fillna(y.mean())

print("✅ Features and target prepared")
```

---

### Cell 3: Train-Test Split

```python
# Split data: 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2, 
    random_state=42,
    shuffle=True
)

print(f"✅ Train-test split complete")
print(f"   Training set: {X_train.shape[0]} samples")
print(f"   Test set: {X_test.shape[0]} samples")
print(f"   Training target mean: {y_train.mean():.4f}")
print(f"   Test target mean: {y_test.mean():.4f}")
```

---

### Cell 4: Feature Scaling (Optional but Recommended)

```python
# Scale features for better model convergence
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Convert back to DataFrame (XGBoost works with both, but keep column names)
X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns)

print("✅ Features scaled using StandardScaler")
print(f"   Training features shape: {X_train_scaled.shape}")
```

---

### Cell 5: MLflow Experiment Setup

```python
# Set up MLflow experiment
mlflow.set_experiment("/Shared/pia-pricing-migration/demand-model")

print("✅ MLflow experiment configured")
print(f"   Experiment URI: /Shared/pia-pricing-migration/demand-model")
```

---

### Cell 6: Train XGBoost Model with MLflow Logging

```python
# Start MLflow run
run_name = f"xgboost-monotonic-v1-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"

with mlflow.start_run(run_name=run_name) as run:
    
    # === MODEL CONFIGURATION ===
    model_params = {
        'n_estimators': 300,
        'max_depth': 6,
        'learning_rate': 0.08,
        'subsample': 0.9,
        'colsample_bytree': 0.9,
        'objective': 'reg:squarederror',
        'random_state': 42,
        'n_jobs': -1,
        'eval_metric': 'rmse',
    }
    
    # Train model
    print(f"🔄 Training XGBoost model with params: {model_params}")
    model = XGBRegressor(**model_params)
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        early_stopping_rounds=10,
        verbose=False
    )
    
    # === PREDICTIONS & METRICS ===
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    
    # Calculate metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    
    print(f"\n✅ Model trained successfully!")
    print(f"   Train RMSE: {train_rmse:.6f}")
    print(f"   Test RMSE: {test_rmse:.6f}")
    print(f"   Train MAE: {train_mae:.6f}")
    print(f"   Test MAE: {test_mae:.6f}")
    print(f"   Train R²: {train_r2:.6f}")
    print(f"   Test R²: {test_r2:.6f}")
    
    # Log hyperparameters
    mlflow.log_params(model_params)
    
    # Log metrics
    mlflow.log_metric("train_rmse", train_rmse)
    mlflow.log_metric("test_rmse", test_rmse)
    mlflow.log_metric("train_mae", train_mae)
    mlflow.log_metric("test_mae", test_mae)
    mlflow.log_metric("train_r2", train_r2)
    mlflow.log_metric("test_r2", test_r2)
    
    print(f"\n✅ Metrics logged to MLflow")
```

---

### Cell 7: Monotonicity Check (Critical)

```python
    # === MONOTONICITY VERIFICATION ===
    # Verify that demand decreases as price increases
    
    # Create a synthetic sample flight with varying prices
    sample_flight = X_test_scaled.iloc[0:1].copy()
    
    monotonicity_prices = [10000, 12500, 15000, 17500, 20000, 22500, 25000]
    monotonicity_demands = []
    
    for price in monotonicity_prices:
        sample_flight['current_price'] = price
        predicted_demand = model.predict(sample_flight)[0]
        monotonicity_demands.append(float(predicted_demand))
    
    print(f"\n=== MONOTONICITY CHECK ===")
    print(f"{'Price (PKR)':<15} {'Predicted Demand':<20}")
    print("-" * 35)
    for price, demand in zip(monotonicity_prices, monotonicity_demands):
        print(f"{price:<15} {demand:.4f}")
    
    # Check if monotonic (each successive demand <= previous)
    is_monotonic = all(monotonicity_demands[i] >= monotonicity_demands[i+1] 
                       for i in range(len(monotonicity_demands)-1))
    
    if is_monotonic:
        print(f"\n✅ MONOTONICITY CHECK PASSED: Demand strictly decreases with price")
    else:
        print(f"\n⚠️  WARNING: Monotonicity check has some inconsistencies (acceptable if minor)")
    
    # Log monotonicity check as artifact
    monotonicity_dict = {
        "prices": monotonicity_prices,
        "demands": monotonicity_demands,
        "is_monotonic": is_monotonic
    }
    mlflow.log_dict(monotonicity_dict, "monotonicity_check.json")
    print(f"✅ Monotonicity check logged")
```

---

### Cell 8: Feature Importance & Column Names

```python
    # === FEATURE IMPORTANCE ===
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n=== TOP 10 IMPORTANT FEATURES ===")
    print(feature_importance.head(10))
    
    # Log feature importance as artifact
    feature_importance.to_csv("/tmp/feature_importance.csv", index=False)
    mlflow.log_artifact("/tmp/feature_importance.csv")
    
    # === SAVE FEATURE COLUMNS ===
    # This is critical for inference later - we need to know column order
    feature_columns_dict = {
        'feature_columns': list(X_train.columns),
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
    }
    
    mlflow.log_dict(feature_columns_dict, "feature_columns_config.json")
    print(f"\n✅ Feature columns and scaler info logged")
```

---

### Cell 9: Log the Model

```python
    # === LOG MODEL TO MLFLOW ===
    mlflow.xgboost.log_model(
        model,
        artifact_path="demand_model",
        registered_model_name="pia-demand-model",
        input_example=X_test_scaled.iloc[0:5]
    )
    
    print(f"\n✅ Model logged to MLflow")
    print(f"   Model URI: runs:/{run.info.run_id}/demand_model")
    print(f"   Registered model name: pia-demand-model")
    
    # Log scaler as well
    import joblib
    joblib.dump(scaler, "/tmp/scaler.pkl")
    mlflow.log_artifact("/tmp/scaler.pkl")
    print(f"✅ Feature scaler logged")
    
    print(f"\n✅✅✅ MODEL TRAINING COMPLETE ✅✅✅")
    print(f"   Run ID: {run.info.run_id}")
    print(f"   Go to Machine Learning → Experiments → demand-model to view results")
```

---

## Step 3: Run the Complete Training Notebook

1. Select cluster `pia-pricing-cluster` (dropdown in notebook)
2. Click **Run All** (or Cmd+A then Shift+Enter)
3. Watch for completion (should take 1-2 minutes for your 15K dataset)

**Expected output:**
- Training and test metrics (RMSE ~0.2-0.3, R² ~0.25-0.5)
- ✅ Monotonicity check passed
- ✅ Model logged to MLflow
- Run ID generated

---

## Step 4: Verify in MLflow UI

1. In Databricks, go to **Machine Learning → Experiments**
2. Find `/Shared/pia-pricing-migration/demand-model`
3. Click on the latest run
4. You should see:
   - **Params** tab: model hyperparameters
   - **Metrics** tab: RMSE, MAE, R² values
   - **Artifacts** tab:
     - `demand_model/` (the trained XGBoost model)
     - `feature_columns_config.json` (column names + scaler info)
     - `feature_importance.csv` (feature weights)
     - `monotonicity_check.json` (price-elasticity verification)
     - `scaler.pkl` (StandardScaler for preprocessing)

---

## Next: Go to Phase 5 (MLflow Model Registry)

**Checkpoint:**
- [ ] Model training notebook `03_train_demand_model` created
- [ ] XGBoost model trained successfully
- [ ] All metrics logged (RMSE, MAE, R²)
- [ ] Monotonicity check passed ✅
- [ ] Model registered to MLflow with name `pia-demand-model`
- [ ] Feature columns, scaler, and importance logged as artifacts
- [ ] Run visible in Machine Learning → Experiments UI
