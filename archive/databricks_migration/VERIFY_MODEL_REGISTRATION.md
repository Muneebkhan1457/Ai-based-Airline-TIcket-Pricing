# How to Verify Model Registration in MLflow

## METHOD 1: Check in Databricks UI (Easiest)

1. Go to your **Databricks workspace**
2. Left sidebar → **Models**
3. Look for **`pia-demand-model`**
4. Click it → should show:
   - ✅ Name: `pia-demand-model`
   - ✅ Version: 1
   - ✅ Stage: Staging (or Production)
   - ✅ Last modified: Today's date

---

## METHOD 2: Add This Cell in Databricks

```python
# Check model registration
import mlflow

# List all registered models
client = mlflow.tracking.MlflowClient()
models = client.search_registered_models()

print("✅ Registered Models:")
for model in models:
    print(f"   Name: {model.name}")
    print(f"   Versions: {len(model.latest_versions)}")
    for version in model.latest_versions:
        print(f"      v{version.version}: {version.status}")
    print()

# Specifically check for pia-demand-model
try:
    model_info = client.get_registered_model("pia-demand-model")
    print(f"✅ FOUND: pia-demand-model")
    print(f"   Status: {model_info.latest_versions[0].status}")
    print(f"   Version: {model_info.latest_versions[0].version}")
except:
    print("❌ NOT FOUND: pia-demand-model")
```

---

## METHOD 3: Load the Model (Verify It Works)

```python
# Try to load the registered model
import mlflow.pyfunc

try:
    model = mlflow.pyfunc.load_model("models:/airline_daw.default.pia-demand-model/1")
    print("✅ Model loaded successfully!")
    print(f"   Type: {type(model)}")
    print(f"   Ready to use for predictions")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
```

---

## METHOD 4: Check MLflow Tracking Server

```python
# Get model details from MLflow
import mlflow

mlflow.set_tracking_uri("databricks")

# Get experiment
experiment = mlflow.get_experiment_by_name("/Users/khaamuneeb420@gmail.com/pia-demand-model")
if experiment:
    print(f"✅ Experiment found: {experiment.name}")
    print(f"   Experiment ID: {experiment.experiment_id}")
    
    # Get runs
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    if len(runs) > 0:
        print(f"\n✅ Found {len(runs)} run(s)")
        for idx, run in enumerate(runs, 1):
            print(f"\n   Run {idx}:")
            print(f"      Run ID: {run.run_id}")
            print(f"      Status: {run.status}")
            print(f"      Params: {run.data.params}")
            print(f"      Metrics: {run.data.metrics}")
else:
    print("❌ Experiment not found")
```

---

## EXPECTED OUTPUT IF REGISTERED ✅

```
✅ FOUND: pia-demand-model
   Status: READY
   Version: 1

✅ Model loaded successfully!
   Type: <class 'mlflow.pyfunc.PyFuncModel'>
   Ready to use for predictions
```

---

## WHAT IF IT SHOWS ❌ NOT FOUND?

**Possible issues:**

1. **Phase 5 didn't run successfully**
   - Look for errors in the cell output
   - Re-run Phase 5

2. **Model name is different**
   - Check what name appears in Databricks UI → Models
   - Use that exact name in Phase 6

3. **Model version is different**
   - Instead of v1, use the correct version number
   - Example: `models:/airline_daw.default.pia-demand-model/2`

---

## QUICK CHECK: Run This Now

Add this cell to your Databricks notebook right after Phase 5:

```python
# QUICK VERIFICATION
print("\n" + "=" * 70)
print("MODEL REGISTRATION VERIFICATION")
print("=" * 70)

import mlflow

try:
    model = mlflow.pyfunc.load_model("models:/airline_daw.default.pia-demand-model/1")
    print("\n✅✅✅ MODEL IS REGISTERED AND READY! ✅✅✅\n")
    print("Status: PRODUCTION READY")
    print("Name: pia-demand-model")
    print("Version: 1")
    print("Can be used in Phase 6 (Pricing Engine)")
    
except Exception as e:
    print(f"\n❌ MODEL NOT FOUND: {e}\n")
    print("Action: Re-run Phase 5 and check for errors")
```

---

## Summary

| Check | Command | Expected |
|-------|---------|----------|
| **UI** | Databricks → Models | See `pia-demand-model` |
| **Code** | `mlflow.pyfunc.load_model(...)` | Returns model object |
| **List** | `client.search_registered_models()` | `pia-demand-model` in list |
| **Status** | Check version status | `READY` or `PRODUCTION` |

✅ If all checks pass → Ready for Phase 6!
