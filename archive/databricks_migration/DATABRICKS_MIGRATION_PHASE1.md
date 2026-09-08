# Phase 1: Cluster Setup & Configuration

## Step 1: Create a New Cluster

1. In Databricks UI, left sidebar → **Compute**
2. Click **Create Cluster**
3. Configure as follows:

| Setting | Value | Reason |
|---------|-------|--------|
| **Cluster Name** | `pia-pricing-cluster` | Easy to identify |
| **Databricks Runtime** | Latest ML Runtime (e.g., `14.3 LTS ML`) | Pre-installs XGBoost, MLflow, scikit-learn, pandas |
| **Node Type** | Default (single node for Community Edition) | Community Edition enforces this |
| **Workers** | 0 (single-node mode) | No distributed computing needed for 15K rows |
| **Autotermination** | 30 minutes | Saves resources; cluster auto-stops when idle |

4. Click **Create Cluster** and wait for it to start (1-2 minutes)

---

## Step 2: Verify Pre-Installed Packages

Once the cluster is running, create a quick test notebook:

1. **Workspace** → navigate to your `pia-pricing-migration` folder
2. Right-click → **New** → **Notebook**
   - Name: `00_verify_packages`
   - Language: **Python**
   - Cluster: Select your `pia-pricing-cluster`
3. In the first cell, run:
   ```python
   import xgboost
   import sklearn
   import pandas
   import mlflow
   import joblib

   print("✅ XGBoost:", xgboost.__version__)
   print("✅ Scikit-learn:", sklearn.__version__)
   print("✅ Pandas:", pandas.__version__)
   print("✅ MLflow:", mlflow.__version__)
   print("✅ Joblib:", joblib.__version__)
   ```
4. Click **Run** (or Shift+Enter)

**Expected output:** All packages import successfully with version numbers.

---

## Step 3: Install Additional Packages (If Needed)

If you need packages NOT pre-installed (e.g., `playwright`, `requests`, `beautifulsoup4` for scrapers):

In a notebook cell, run:
```python
%pip install playwright requests beautifulsoup4
```

Wait for completion (shows "Successfully installed...").

**Note:** For Community Edition single-node, this is fine. For larger clusters, use init scripts or cluster policies (more advanced; not needed here).

---

## Step 4: Configure MLflow Tracking

MLflow is pre-configured automatically on Databricks, but let's verify:

In a new notebook cell:
```python
import mlflow

# Check default tracking URI (should be Databricks)
print("Tracking URI:", mlflow.get_tracking_uri())

# Set experiment path for our project
mlflow.set_experiment("/Shared/pia-pricing-migration/demand-model")

# List experiments to confirm
experiments = mlflow.search_experiments()
for exp in experiments:
    print(f"Experiment: {exp.name}")
```

Run this cell. You should see the experiment created in `Machine Learning → Experiments` in the Databricks UI.

---

## Next: Go to Phase 2 (Data Migration)

**Checkpoint:**
- [ ] Cluster `pia-pricing-cluster` created and running
- [ ] All required packages verified (XGBoost, scikit-learn, MLflow, etc.)
- [ ] MLflow experiment space configured
- [ ] Test notebook runs successfully
