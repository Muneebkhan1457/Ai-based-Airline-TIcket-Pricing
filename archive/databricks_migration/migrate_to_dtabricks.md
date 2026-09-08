# PIA Dynamic Pricing — Databricks + MLflow Migration Guide

**Purpose:** Step-by-step plan to move the already-built, locally-working MVP (Data layer → Demand model → Pricing engine → Scheduler → API → Dashboard → Backtest) onto Databricks, with MLflow as the model tracking/registry layer, per the instruction: train locally is done, everything from model registration onward happens on Databricks with MLflow.

**Starting point:** Databricks Community Edition (free tier), no existing workspace — this guide starts from account creation.

**Local project reference:** `C:\Users\pc\Desktop\data` — already has a fully working, tested pipeline (11/11 tests passing, R²=0.48 monotonic demand model, working pricing engine, scheduler, FastAPI, Streamlit dashboard, backtest showing revenue uplift).

---

## Phase 0 — Databricks Account Setup

1. Go to `https://community.cloud.databricks.com/login.html` (Community Edition — always free, no credit card).
2. Sign up with email, verify, log in.
3. You land in a workspace with:
   - **Compute** — where you create clusters
   - **Workspace** — where notebooks live
   - **Data** — for uploading/managing data (DBFS, Unity Catalog on paid tiers)
   - **Machine Learning** → **Experiments** and **Models** — this is MLflow's UI, built into Databricks

**Community Edition limitations to keep in mind:**
- Single-node cluster only, auto-terminates after idle time — fine for this project's data size (15,000 rows)
- No Databricks Jobs scheduling on the free tier in some regions — may affect how Phase 5 (autonomous scheduler) is ported; verify this once inside the workspace, and have a fallback plan (see Phase 6 below)
- Limited storage, but the whole `flight.db` is only ~1MB, not a concern

---

## Phase 1 — Cluster Setup

1. In Databricks, go to **Compute** → **Create Cluster**.
2. Use the default/latest Databricks Runtime with ML support (look for a runtime version tagged "ML" — it comes with `mlflow`, `xgboost`, `scikit-learn`, `pandas` pre-installed, saving setup time).
3. Start the cluster (Community Edition clusters are small and may take a minute to spin up).
4. Any extra packages not pre-installed (e.g. `fastapi`, `streamlit`, `playwright` if needed later) can be installed via a notebook cell: `%pip install fastapi uvicorn streamlit`.

---

## Phase 2 — Data Migration

**Goal:** Get `flight.db`'s two core tables (`flights`, `external_signals`) into Databricks in a usable form.

### Option A — Simple CSV upload (fastest, good for MVP)
1. Locally, export both tables to CSV:
   ```python
   import sqlite3, pandas as pd
   conn = sqlite3.connect("Data_load/flight.db")
   pd.read_sql_query("SELECT * FROM flights", conn).to_csv("flights_export.csv", index=False)
   pd.read_sql_query("SELECT * FROM external_signals", conn).to_csv("external_signals_export.csv", index=False)
   ```
2. In Databricks: **Data** → **Add Data** → **Upload File** → upload both CSVs.
3. This creates tables (or DBFS files) you can load with `spark.read.csv(...)` or `pandas.read_csv("/dbfs/...")` in a notebook.

### Option B — Delta tables (more "proper" Databricks-native approach)
1. Upload the CSVs as above, then convert:
   ```python
   df_flights = spark.read.csv("/FileStore/tables/flights_export.csv", header=True, inferSchema=True)
   df_flights.write.format("delta").mode("overwrite").saveAsTable("pia_pricing.flights")

   df_signals = spark.read.csv("/FileStore/tables/external_signals_export.csv", header=True, inferSchema=True)
   df_signals.write.format("delta").mode("overwrite").saveAsTable("pia_pricing.external_signals")
   ```
2. This gives you a proper managed table queryable via SQL (`SELECT * FROM pia_pricing.flights`) and versioned via Delta Lake — useful if you want to show "we used Delta Lake" as a portfolio point.

**Recommendation:** Start with Option A for speed; upgrade to Option B once the pipeline works end-to-end, since it's a bigger step (schema, Delta format) that shouldn't block early progress.

**Note on live scraping:** The scrapers (fuel, competitor, FX) currently run locally via Playwright/requests. Databricks Community Edition notebooks CAN run `requests`/`BeautifulSoup`-based scraping (fuel, FX) directly. Playwright (competitor scraper) is heavier — it may or may not work cleanly in a Databricks cluster environment; this needs testing in Phase 6. Until then, the historical scraped data (already collected locally) can be migrated as-is via the CSV/Delta approach above, and live re-scraping can continue running locally with results uploaded periodically, if Playwright doesn't work well on cluster.

---

## Phase 3 — Feature Engineering in Databricks

1. Create a new notebook: `01_prepare_dataset`.
2. Port the logic from local `models/prepare_dataset.py` into notebook cells — same logic (departure_date synthesis, competitor min/avg aggregation by route, random-noise fuel/FX signals, holiday window calculation), just reading from the Databricks tables/CSVs instead of local SQLite.
3. Output: a `training_dataset` DataFrame — either kept as a Spark/pandas DataFrame in-notebook, or saved as a Delta table (`pia_pricing.training_dataset`) for reuse across notebooks.
4. Sanity-check: reproduce the same known-good numbers from local runs (price-demand correlation ~-0.19 to -0.41 depending on which fix stage, competitor coverage ~40%, holiday window ~13%) to confirm the migration didn't silently change any logic.

---

## Phase 4 — Model Training with MLflow Tracking

**This is the core of the Databricks+MLflow integration.**

1. Create notebook: `02_train_demand_model`.
2. MLflow is pre-installed and auto-configured for tracking on Databricks — no manual `mlflow.set_tracking_uri()` needed inside a Databricks notebook (it defaults to the workspace tracking server).
3. Port the training logic from local `models/train_demand_model.py`, wrapped in an MLflow run:

```python
import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd

mlflow.set_experiment("/Shared/pia-dynamic-pricing/demand-model")

with mlflow.start_run(run_name="xgboost-monotonic-v1"):
    # ... load training_dataset, drop leakage columns (id, total_seats,
    # booked_seats, remaining_seats, booking_date), one-hot encode
    # route/flight_class — same logic as local train_demand_model.py

    model = XGBRegressor(
        n_estimators=300, max_depth=6, learning_rate=0.08,
        subsample=0.9, colsample_bytree=0.9,
        objective='reg:squarederror', random_state=42, n_jobs=-1,
        monotone_constraints={'current_price': -1, 'price_vs_competitor_ratio': -1}
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    rmse = mean_squared_error(y_test, preds) ** 0.5
    r2 = r2_score(y_test, preds)

    # log params, metrics
    mlflow.log_params(model.get_params())
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("r2", r2)

    # log the monotonicity check as a metric/artifact too, since this
    # was a critical correctness check in the local version
    monotonicity_prices = [10000, 15000, 20000, 25000]
    monotonicity_demands = [...]  # predict at each price
    mlflow.log_dict(
        {"prices": monotonicity_prices, "demands": monotonicity_demands},
        "monotonicity_check.json"
    )

    # log the trained model itself, tracked by MLflow
    mlflow.xgboost.log_model(model, artifact_path="demand_model")

    # also log the feature column order (equivalent to feature_columns.pkl)
    mlflow.log_dict({"columns": list(X_train.columns)}, "feature_columns.json")
```

4. After running, go to **Machine Learning → Experiments** in the Databricks UI — you'll see this run with its params, metrics, and the logged model artifact. This replaces the local `demand_model.pkl` + `feature_columns.pkl` file pair.

---

## Phase 5 — MLflow Model Registry

**Goal:** Promote the trained model from "just an experiment run" to a versioned, named model that other code can reliably load by name (`models:/pia-demand-model/Production`) instead of a raw file path.

1. From the Experiments UI (or in code), register the model:
```python
result = mlflow.register_model(
    model_uri=f"runs:/{run.info.run_id}/demand_model",
    name="pia-demand-model"
)
```
2. Go to **Machine Learning → Models** → find `pia-demand-model` → you'll see Version 1.
3. Manually (or via API) transition it to a stage, e.g. "Staging" then "Production", once you're satisfied with the monotonicity check and R² (same healthy-range check as before: ~0.25-0.5, monotonic demand curve).
4. Loading the model elsewhere (e.g. in the pricing engine) then becomes:
```python
import mlflow.pyfunc
model = mlflow.pyfunc.load_model("models:/pia-demand-model/Production")
```
This replaces `joblib.load(MODEL_PATH)` in the old `pricing_engine/elasticity.py`.

---

## Phase 6 — Porting the Rest of the Pipeline

This is the part that needs a decision, since Databricks is primarily a notebook/data-processing environment, not a general app-hosting platform. Recommended split:

**Stays as Databricks notebooks/jobs:**
- Data ingestion + feature engineering (Phase 2-3 above)
- Model training + MLflow registration (Phase 4-5 above)
- `pricing_engine/` logic (elasticity, guardrails, optimizer) — this is pure Python/pandas logic, ports cleanly into a notebook or a Databricks-hosted Python module
- Backtest simulation (`backtest/simulate.py`) — this is a batch computation, a natural fit for a Databricks notebook/job

**Recommended to keep running locally (or move later to a proper cloud service, not Community Edition):**
- The FastAPI service (`api/`) — Databricks Community Edition isn't designed to host a persistent, publicly-reachable web API. Options: (a) keep FastAPI running locally/on a small VM and have it call Databricks via the MLflow Model Registry + a Databricks SQL/REST API for data, or (b) if the goal is purely to demonstrate the ML/data workflow on Databricks (common for portfolio purposes), keep the API+UI as a separate "serving layer" that consumes the registered MLflow model, and note in documentation that a full production deployment would use Databricks Model Serving (a paid-tier feature) instead.
- The Streamlit dashboard (`ui/`) — same reasoning; stays local, but now points to the Databricks-hosted model via MLflow rather than a local `.pkl` file.
- The autonomous scheduler (`scheduler/`) — Databricks Jobs (workflow scheduling) may or may not be available on Community Edition; if not, keep `run_autopilot.py` running locally as-is, just pointed at the Databricks-hosted model and Delta tables instead of local SQLite.

**Decide and document this split explicitly** once inside the workspace and Community Edition's actual feature limits are confirmed — this avoids wasted effort trying to force something (like persistent API hosting) into a tier that doesn't support it.

---

## Phase 7 — Updating Local Code to Use the Databricks-Hosted Model

Once Phase 5 is done, `pricing_engine/elasticity.py` needs an update:

```python
# OLD (local file):
# model = joblib.load(MODEL_PATH)

# NEW (Databricks MLflow Registry):
import mlflow

mlflow.set_tracking_uri("databricks")  # requires Databricks CLI auth configured locally
model = mlflow.pyfunc.load_model("models:/pia-demand-model/Production")
```

This requires setting up **Databricks CLI authentication** locally (a personal access token from the Databricks workspace, configured via `databricks configure` or environment variables `DATABRICKS_HOST` / `DATABRICKS_TOKEN`), so that code running outside Databricks (the local FastAPI/Streamlit) can still reach the registered model.

---

## Phase 8 — Re-Verification After Migration

Once the model-loading path is switched to MLflow, re-run the same verification checklist used locally, to confirm nothing broke in translation:
- Monotonicity check (10k/15k/20k/25k PKR → strictly decreasing demand)
- Pricing engine test (KHI-LHE Economy sample → sensible price within guardrails)
- Full API test suite
- Backtest revenue uplift sanity check (should land in the same rough range as before, +15% to +25%)

---

## Open Questions To Resolve Once Inside the Workspace

1. Does this specific Community Edition workspace/region support Databricks Jobs (for scheduling)? If not, Phase 6's scheduler stays local.
2. Does Playwright work in a Databricks cluster's Python environment, or does the competitor scraper need to stay local?
3. Is Unity Catalog available on this Community Edition instance (affects how "proper" the Delta table setup in Phase 2 Option B can be) — Community Edition traditionally does NOT include Unity Catalog, so Delta tables would be workspace-local (hive_metastore) rather than catalog-managed; note this as a known limitation if it comes up, not a bug.

---

## Summary Checklist

- [ ] Phase 0: Databricks Community Edition account created
- [ ] Phase 1: Cluster created and running
- [ ] Phase 2: flights + external_signals data uploaded (CSV or Delta)
- [ ] Phase 3: prepare_dataset logic ported, training_dataset reproduced with matching sanity-check numbers
- [ ] Phase 4: Model trained in a Databricks notebook, logged to MLflow (params, metrics, monotonicity check, model artifact)
- [ ] Phase 5: Model registered in MLflow Model Registry, promoted to Production stage
- [ ] Phase 6: Explicit decision made and documented on what stays on Databricks vs local
- [ ] Phase 7: pricing_engine/elasticity.py updated to load from MLflow Registry instead of local .pkl
- [ ] Phase 8: Full re-verification passed after the migration