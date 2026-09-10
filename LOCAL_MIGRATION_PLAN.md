# Migrate Away from Databricks to Local DagsHub MVP

The goal of this migration is to completely sever dependencies on Databricks/Azure and restore the local setup utilizing the local `flight.db` SQLite database, local Python ETL jobs, and DagsHub for MLflow/DVC.

## Proposed Changes

### 1. `api/services.py` (FastAPI Backend)
- Replace the `databricks.sql` connector with Python's built-in `sqlite3` to connect to the local database at `Data_load/flight.db`.
- Remove the `airline_daw.pia_pricing.` schema prefix from all SQL queries (so it queries SQLite correctly).
- Remove `WorkspaceClient` (Databricks SDK) used for fetching model versions and replace it with `mlflow.MlflowClient().search_model_versions()`.
- Update `mlflow.set_tracking_uri()` and `set_registry_uri()` to rely on environment variables pointing to DagsHub (which were configured earlier).

### 2. `api/main.py` (FastAPI Backend)
- Remove the import `from scheduler.databricks_autopilot import run_etl_and_push`.
- In the `/signals/trigger-etl` endpoint, replace the Databricks logic by importing and triggering the local scraper jobs directly from `scheduler.jobs`.

### 3. `ui/app.py` (Streamlit Dashboard)
- Remove text referring to Databricks (e.g., "Databricks system of record", "Databricks is loading the model") and update them to reflect the local setup.

## Verification Plan
1. Start the API using `uv run uvicorn api.main:app`.
2. Start the Streamlit UI using `uv run streamlit run ui/app.py`.
3. Use the UI to "Trigger Manual ETL Refresh" and ensure background scrapers work.
4. "Reprice ALL Routes" to ensure the SQLite database and local pricing engine function without Databricks errors.
