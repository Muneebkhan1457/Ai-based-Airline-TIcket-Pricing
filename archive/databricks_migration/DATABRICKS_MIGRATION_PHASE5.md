# Phase 5: MLflow Model Registry & Promotion

## Objective
Take the trained model from Phase 4 and register it in MLflow Model Registry, then promote it to "Production" stage so other notebooks can reliably load it.

---

## Step 1: Register the Model

### Via Databricks UI (Easiest):

1. Go to **Machine Learning → Experiments** (left sidebar)
2. Find `/Shared/pia-pricing-migration/demand-model` experiment
3. Click on the latest run (with successful metrics)
4. In the **Artifacts** section, find `demand_model/`
5. Click on `demand_model/` folder
6. Look for a button **"Register Model"** or similar
7. Click it → A dialog appears asking for a model name
8. Enter: `pia-demand-model`
9. Click **Register**

**Result:** Model now appears in **Machine Learning → Models** with Version 1

---

### Via Code (Alternative):

If you want to automate this, in a Databricks notebook cell:

```python
import mlflow

# Get the run ID from Phase 4 (you'll see it in the run details)
run_id = "abc1234567890def"  # Replace with your actual run ID from Phase 4

# Register the model
model_uri = f"runs:/{run_id}/demand_model"
result = mlflow.register_model(
    model_uri=model_uri,
    name="pia-demand-model"
)

print(f"✅ Model registered: {result.name} Version {result.version}")
```

---

## Step 2: Verify Model Registration

1. Go to **Machine Learning → Models** (left sidebar)
2. You should see `pia-demand-model` in the list
3. Click on it to see:
   - **Version 1**: Your trained model from Phase 4
   - **Stage**: None (default)
   - **Description**: (empty)

**Screenshot checkpoint:** Take a screenshot for your professor showing the model in the registry.

---

## Step 3: Promote to Production Stage

1. In the Models UI, click on `pia-demand-model` → **Version 1**
2. You'll see details:
   - Trained XGBoost model
   - All metrics from Phase 4
   - Artifacts (demand_model/, feature_columns_config.json, etc.)
3. Look for a **"Stage"** dropdown (top right or in model details)
4. Change from **None** → **Staging**
5. Click **Confirm** (if prompted)

Now repeat:
6. Change from **Staging** → **Production**
7. Click **Confirm**

**Result:** Version 1 is now in "Production" stage. Other code will load from this stage.

---

## Step 4: Test Loading the Model

Create a quick test notebook to verify loading works:

**New notebook:** `04_test_model_loading`  
**Language:** Python  
**Cluster:** `pia-pricing-cluster`

```python
import mlflow
import mlflow.pyfunc
import pandas as pd

# Load the model from the Production stage
print("🔄 Loading model from MLflow Registry...")
model = mlflow.pyfunc.load_model("models:/pia-demand-model/Production")

print("✅ Model loaded successfully!")

# Test a prediction
# Create a sample input matching the feature set from Phase 3
sample_data = {
    'days_to_departure': [3],
    'is_weekend': [1],
    'fuel_price': [330.5],
    'usd_pkr_rate': [277.86],
    'competitor_min_price': [14500],
    'competitor_avg_price': [17800],
    'price_vs_competitor_ratio': [0.95],
    'is_holiday_window': [1],
    'remaining_capacity_ratio': [0.45],
    # ... add all other features from training_dataset
    # (you can check exact features in feature_columns_config.json from Phase 4 artifacts)
}

sample_df = pd.DataFrame(sample_data)

# Predict
prediction = model.predict(sample_df)
print(f"\n✅ Sample Prediction: {prediction[0]:.4f} (demand ratio)")

print("\n✅✅ Model loading test PASSED!")
```

**Expected output:**
```
✅ Model loaded successfully!
✅ Sample Prediction: 0.6234 (demand ratio)
✅✅ Model loading test PASSED!
```

If you get an error, double-check:
- Model name is exactly `pia-demand-model` (case-sensitive)
- Stage is set to "Production"
- Features in sample_df match the training dataset schema

---

## Step 5: Document Model Version Info

Create a reference document for Phases 6+ about what the model expects:

**New notebook:** `04b_model_metadata`  
**Language:** Python

```python
import mlflow
import mlflow.pyfunc
import json

# Load model and inspect metadata
model = mlflow.pyfunc.load_model("models:/pia-demand-model/Production")

# Get run info
run_info = mlflow.get_run(model.metadata.run_id)

print("=== Model Metadata ===")
print(f"Model Name: pia-demand-model")
print(f"Version: {model.metadata.version}")
print(f"Stage: Production")
print(f"Run ID: {model.metadata.run_id}")

print(f"\n=== Training Metrics ===")
for metric_name, metric_value in run_info.data.metrics.items():
    print(f"{metric_name}: {metric_value:.6f}")

print(f"\n=== Hyperparameters ===")
for param_name, param_value in run_info.data.params.items():
    print(f"{param_name}: {param_value}")

# Load the feature config from artifacts
artifacts_dir = f"/dbfs/mlruns/{run_info.info.experiment_id}/{run_info.info.run_id}/artifacts"

import os
config_path = f"{artifacts_dir}/feature_columns_config.json"

if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"\n=== Feature Configuration ===")
    print(f"Expected input columns: {len(config['feature_columns'])}")
    print(f"Columns: {config['feature_columns']}")
else:
    print("Warning: feature_columns_config.json not found in artifacts")

print("\n✅ Model metadata documented")
```

Run this to confirm all metadata is correctly logged.

---

## Checkpoint: Phase 5 Complete ✅

Before moving to Phase 6, verify:

- [ ] Model `pia-demand-model` exists in MLflow Model Registry
- [ ] Version 1 is in "Production" stage
- [ ] Test notebook `04_test_model_loading` successfully loads and predicts
- [ ] All metrics visible (RMSE, MAE, R²)
- [ ] Artifacts visible (demand_model/, feature_columns_config.json, etc.)

---

## What Happens in Phase 6+

All downstream notebooks (pricing engine, scheduler, API, etc.) will load the model like this:

```python
import mlflow.pyfunc
model = mlflow.pyfunc.load_model("models:/pia-demand-model/Production")
```

Instead of the old way:
```python
import joblib
model = joblib.load("models/demand_model.pkl")
```

This means:
- ✅ Model versioning (track all versions)
- ✅ Governance (who trained it, when, with what data)
- ✅ Easy rollback (revert to older version if needed)
- ✅ Reproducibility (exact same model every time)

---

## Next: Go to Phase 6 (Pricing Engine)

Once Phase 5 checkpoint passes, I'll provide Phase 6 which ports your pricing engine to Databricks using this registered model.

**Estimated time to reach here:** ~1 hour from start
**Remaining:** ~1 hour for Phases 6-10
