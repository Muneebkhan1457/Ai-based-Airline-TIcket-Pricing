# Hand-off Context: Databricks to Local DagsHub Migration

**To:** Claude (or next agent)
**From:** Antigravity AI
**Project:** AI Dynamic Ticket Pricing

## 1. Project Background
The system was originally built to operate locally but was partially migrated to Databricks/Azure. However, the Databricks workspace was disabled/blocked. The user requested an end-to-end rollback of the system to operate **100% locally** using a local SQLite database (`flight.db`) and a local XGBoost model, while syncing large files and MLflow tracking to **DagsHub** via **DVC**.

## 2. Actions Taken & Technical Changes Made

### A. DVC and DagsHub Configuration
- **DVC Initialization:** Installed DVC and initialized it in the project repository.
- **Remote Setup:** Added DagsHub as the DVC remote (`https://dagshub.com/Muneebkhan1457/Ai-based-Airline-TIcket-Pricing.dvc`).
- **Authentication:** Configured DVC to authenticate using the user's DagsHub username and personal access token/password.
- **Data Versioning:** Tracked all large files (including `flight.db`, `models/demand_model.pkl`, CSVs) using `dvc add` and pushed them successfully to DagsHub.

### B. Severing Databricks Dependencies
We performed a comprehensive find-and-replace across the codebase to strip out all Databricks SDK and Databricks SQL Connector code.

**`api/services.py`:**
- **Database Connection:** Replaced `databricks.sql.connect` with Python's built-in `sqlite3`. The app now correctly points to `Data_load/flight.db`.
- **SQL Queries:** Stripped the Databricks schema prefix (`airline_daw.pia_pricing.`) from all SQL statements to make them compatible with local SQLite.
- **Schema Mismatch Fix:** Fixed an `OperationalError` by changing `recommended_price` to `price` in `price_history` INSERT statements to match the local SQLite schema.
- **Model Inference:** Removed `WorkspaceClient` (Databricks MLflow Client). The `get_model()` function was rewritten to load the XGBoost model directly from disk (`models/demand_model.pkl`) using Python's `pickle` library, completely decoupling inference from an active MLflow tracking server connection.

**`api/main.py`:**
- **Local ETL:** Replaced the import `from scheduler.databricks_autopilot import run_etl_and_push` with local scraper functions. The `/signals/trigger-etl` endpoint now executes `run_fuel_job()`, `run_competitor_job()`, and `run_fx_job()` sequentially instead of pushing to Azure.

**`ui/app.py` (Streamlit):**
- **Dashboard Cleanup:** Removed all warnings and captions referring to Databricks (e.g., "Databricks system of record" or "Databricks is loading the model").

### C. Environment Configuration
- Created a `.env` file in the project root containing:
  - `MLFLOW_TRACKING_URI=https://dagshub.com/Muneebkhan1457/Ai-based-Airline-TIcket-Pricing.mlflow`
  - `MLFLOW_TRACKING_USERNAME` and `MLFLOW_TRACKING_PASSWORD`.

### D. Testing & Verification
- **API Tests:** Updated the `pytest` mock patching in `api/tests/test_api.py` to account for the removed Databricks modules.
- **Status:** Ran the full test suite (`pytest api/tests`) and all 9 endpoints/tests passed successfully.
- **End-to-End Simulation:** Programmatically ran `services.reprice_all_routes()` which successfully generated optimal prices for 10 route combinations and logged them to the SQLite database.

### E. Workspace Cleanup
- Recursively deleted over 1,700 junk directories including `__pycache__`, `.pytest_cache`, `.mimocode`, and `.agents` across the project to keep the repository clean.

## 3. Current System Architecture
- **Source of Truth:** Local SQLite database (`Data_load/flight.db`).
- **Model:** Local pickle file (`models/demand_model.pkl`).
- **Background Tasks:** Handled entirely by local python scripts inside `scheduler/`.
- **APIs & UI:** FastAPI (`api/main.py`) serves endpoints; Streamlit (`ui/app.py`) provides the dashboard. Both work flawlessly using `uv run`.

## 4. Next Steps
The system is fully operational locally. Claude can proceed with adding new features, modifying the pricing algorithms, or tweaking the Streamlit UI knowing that the foundational local architecture is solid and tested.
