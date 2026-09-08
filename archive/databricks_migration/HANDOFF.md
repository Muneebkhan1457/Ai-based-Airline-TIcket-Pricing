# PIA AI Dynamic Ticket Pricing — Databricks Migration Handoff

> **Purpose:** Full handoff document so any fresh agent can continue exactly where we left off.
> Written: 2026-08-05. Working dir: `C:\Users\pc\Desktop\data` (git repo, Windows, PowerShell).

---

## 1. Big Picture / Goal

Shift the **local** PIA airline ticket pricing MVP to **Databricks + MLflow**, then fix its gaps:

1. FastAPI must use the **real MLflow model** (registered in UC: `airline_daw.default.pia-demand-model`) — not hardcoded numbers.
2. History / signals endpoints must return **real data** from Databricks.
3. Add a **local autopilot** that: runs existing scrapers → mirrors fresh signals to Databricks → delta-checks → reprices affected routes using the MLflow model → persists to `price_history`.

**User's architecture decisions (do NOT change):**
- **Local autopilot** — APScheduler runs on the user's PC.
- **Dual source** — scrapers keep writing to local `Data_load\flight.db` (SQLite) unchanged; autopilot mirrors fresh signals into Databricks. Databricks + MLflow model is the system of record.
- **"Don't change anything"** in the existing local scrapers/ETL/pricing engine.

---

## 2. Environment Setup (done)

- `uv` project. Venv at `C:\Users\pc\Desktop\data\.venv`.
- `pyproject.toml` (was empty) now has `[tool.uv] package = false` and dependencies:
  `databricks-sql-connector`, `mlflow`, `pandas`, `numpy`, `scikit-learn`, `xgboost`, `joblib`, `fastapi`, `uvicorn`, `httpx`, `streamlit`, `requests`, `apscheduler`, `python-dotenv`, `beautifulsoup4`, `playwright==1.61.0`.
- Installed via `uv sync` — works (playwright browsers already cached in `%LOCALAPPDATA%\ms-playwright`).

**`.env` (in project root):**
```
DATABRICKS_HOST=adb-7405617912719706.6.azuredatabricks.net
DATABRICKS_TOKEN=dapi_masked_for_security
DATABRICKS_WAREHOUSE=3beec695f0d86f89
```
> Old token `e775a...` worked only for SQL warehouse, NOT for Workspace REST API (401).
> New token must be a real **PAT starting with `dapi`**.

**Critical MLflow settings (in `api/services.py`):**
- `mlflow.set_tracking_uri("databricks")` + `mlflow.set_registry_uri("databricks-uc")` (registry MUST be UC for model registry access).
- Model fetch: `WorkspaceClient.model_versions.list(MODEL_NAME)` + filter `v.status.value == "READY"` (enum has `.value`).

**Model:** `airline_daw.default.pia-demand-model`, 8 versions, latest **v8 READY**.
**Catalog/schema:** `airline_daw.pia_pricing` tables: `flights`, `external_signals`, `price_history`.

**Known harmless warning:** MLflow dependency-mismatch (numpy 2.5.1 vs 2.1.3, etc.) — ignore.

---

## 3. What We Solved / Status (step-by-step)

### Step 1 — Dependencies ✅ DONE
`uv sync` works, model loads (`Loaded airline_daw.default.pia-demand-model v8`).

### Step 2 — `api/services.py` rewritten ✅ DONE & VERIFIED
Real MLflow model engine. Key functions:
- DB connection (SQL Warehouse via `databricks-sql-connector`).
- `load_model()` — latest READY version via WorkspaceClient SDK.
- `predict_demand(context, total_seats, remaining_seats)` → dict with `predicted_demand_ratio`, `expected_revenue`, etc.
- `predict_demand_at_price(context, price)` — for price-scan.
- `optimize_price(context, total_seats, remaining_seats)` — scans 108 price candidates, returns best `(recommended_price, expected_revenue, predicted_demand_ratio)`.
- `ensure_schema()` — creates `price_history` if missing; column is **`recommended_price`** (NOT `price`).
- `insert_price_history(records)`, `get_latest_price_history(limit)`.
- `get_representative_flight(route, flight_class)`, `get_base_fare(...)`, `get_competitor_stats(...)`.
- `reprice_all_routes(trigger_reason="batch_trigger")` — all 5 routes × 2 classes.
- `get_signals_history(limit)`.
- `check_health()`.

**Verified real outputs:**
- `recommend KHI-LHE Economy → 10475.98 PKR`, revenue 942838.22, demand 0.6424, 108 candidates.
- Monotonic demand: `@15000 = 0.4959` > `@25000 = 0.2894` (correct).
- Timezone fix applied: holidays use `dates.tz_localize(None)`.
- Emoji removed (Windows cp1252 can't print `✅`).

### Step 3 — `api/main.py` endpoints ✅ DONE & VERIFIED
- `POST /pricing/recommend` → real model (works).
- `POST /pricing/predict-demand-at-price` → works.
- `GET /pricing/history/latest` → real rows from Databricks (works).
- `GET /signals/history` → real rows (works).
- `POST /pricing/batch-reprice` → calls `services.reprice_all_routes("batch_trigger")` — **VERIFIED: wrote 10 route/class records to Databricks price_history.**
- `POST /signals/trigger-etl` → imports `from scheduler.databricks_autopilot import run_etl_and_push`.

**Verified all endpoints** via FastAPI TestClient:
```
health: 200 {status: ok, database_connected: True, model_loaded: True}
recommend: 200 {price 10475.98, demand 0.6424}
demand@20000: 200 {0.3303}
history: 200 (3 rows)
signals: 200 (3 rows)
batch-reprice: 200 {routes_repriced: 10}
```

### Step 4 — `scheduler/databricks_autopilot.py` ✅ CREATED (was missing; now works)
New file. Functions:
- `get_local_signals()` — reads all rows from local `flight.db` external_signals.
- `push_signals_to_databricks()` — dedupe by `(route, signal_type, recorded_date)` against existing Databricks rows; inserts only new ones. **Fixed bugs:**
  1. String-vs-datetime comparison error (`'<=' not supported between 'str' and 'datetime.datetime'`) — added `_norm_date()`.
  2. Old dedupe used `MAX(recorded_date)` which was wrong because future holidays (2026-12-25) are pre-loaded → nothing ever pushed. Now uses per-key existence set.
- `run_etl_and_push()` — runs `init_db()`, `run_fuel_job()`, `run_competitor_job()`, `run_fx_job()` (unchanged local jobs) then pushes.
- `_latest_databricks_signals()` — latest value per `(route, signal_type)` using `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY recorded_date DESC)`. **Fixed bug:** old version only took `MAX(recorded_date)` rows, so future holidays masked all real signal changes.
- `check_for_changes()` — OR-delta check, in-memory baseline. **Fixed bug:** `global_changed` now True when any `GLOBAL` signal changes (old code only checked `route is None`).
- `scheduled_check()` — one full cycle: ETL+push → delta → reprice affected routes (all routes if global change) → insert `delta_trigger` records.
- `main()` — APScheduler `BlockingScheduler`, every 10 minutes, immediate first run.

**Autopilot tests pass:**
- `push_signals_to_databricks()` → 0 pushed (all local signals already in Databricks — correct dedupe).
- `check_for_changes()` baseline → detects 10 changed keys incl. GLOBAL signals, `global_changed: True`, affected routes `{KHI-ISB, KHI-LHE}`; second run → no change.
- `_reprice_route("KHI-LHE")` writes `delta_trigger` records (test aborted by user mid-run, but the batch flow was already proven).

### Step 5 — UI (`ui/app.py` Tab 3) ❌ NOT DONE
Streamlit Tab 3 still a placeholder. Must wire to `GET /signals/history`.

### Step 6 — Notebook `00_verify_packages (1).ipynb` ⚠️
- 9 cells (schema/volume, flights, PHASE3 signals, PHASE4 features, PHASE5 training+MLflow, PHASE6 pricing engine, PHASE7 scheduler-static, PHASE10 backtest, + 1 empty cell at line 1605).
- Redundant cell (Load training dataset / train-test split before PHASE 5) was deleted earlier by user.
- Empty last cell can be deleted.
- PHASE 7 scheduler is **static** (no real scraping) — that's expected; the real autopilot now lives locally.

### Step 7 — Tests ❌ NOT DONE
`api/tests/test_api.py` exists but not run/updated for this new backend.

---

## 4. What's Remaining (in order)

1. **Step 5 — Streamlit Tab 3** in `ui/app.py`: replace placeholder with real calls to `GET /signals/history` (mirror the style of Tab 2 history). Run `streamlit run ui/app.py` to verify.
2. **Fix local `price_history` mismatch** (optional): the local `flight.db` `price_history` has column `price`, Databricks has `recommended_price`. The autopilot writes to Databricks via `services.insert_price_history` — fine. Only relevant if something reads the local table.
3. **Step 7 — Run the real test suite**: `uv run pytest api/tests/` and fix failures (schemas may need `recommended_price` naming). There is a `api/schemas.py` — verify response models match actual field names.
4. **Final end-to-end autopilot cycle:** `uv run python -m scheduler.databricks_autopilot` (or POST `/signals/trigger-etl`), confirm Databricks `external_signals` + `price_history` update and no exceptions. NOTE: competitor scraper takes ~2 min (playwright headless browser times out on sastaticket — site structure). The autopilot already treats scraper failure gracefully (continues with existing data).
5. **Optional**: delete the empty last cell in the notebook.
6. **Optional**: `ui/app.py` Tab "Batch Reprice" already wired to `POST /pricing/batch-reprice`? Verify.

---

## 5. Key File Map

| File | State | Notes |
|---|---|---|
| `api/services.py` | ✅ Done | Real MLflow engine; verified |
| `api/main.py` | ✅ Done | All endpoints wired; verified |
| `api/schemas.py` | ⚠️ Verify | May need field-name updates |
| `scheduler/databricks_autopilot.py` | ✅ Done | New autopilot (was missing) |
| `scheduler/jobs.py`, `run_autopilot.py`, `delta_check.py` | ⚠️ Legacy | Local original autopilot, unchanged. New one supersedes these |
| `scheduler/jobs.py` runs scrapers via subprocess | ✅ | Fuel/FX work; competitor works but times out on site |
| `ui/app.py` | ❌ Step 5 | Tab 3 still placeholder |
| `Data_load\scrapers\*.py` (3 scrapers) | ✅ unchanged | fuel (bs4), competitor (playwright), fx (requests) |
| `.env` | ✅ | New valid PAT |
| `pyproject.toml` | ✅ | All deps incl. bs4 + playwright |
| `00_verify_packages (1).ipynb` | ⚠️ | 1 empty cell; redundant cell already deleted |
| `api/tests/test_api.py` | ❌ Not run | Needs updating |

**Databricks tables (`airline_daw.pia_pricing`):**
- `external_signals`: `id int, route string, signal_type string, value double, unit string, source string, recorded_date timestamp, scraped_at date`
- `price_history`: `route, flight_class, recommended_price, expected_revenue, predicted_demand_ratio, trigger_reason, recorded_at`
- `flights`: route/class flight inventory (source of base_fare, seats).

**Local `flight.db` `external_signals`:** `id, route, signal_type, value, unit, source, recorded_date, scraped_at` (same). Note route `GLOBAL` for petrol/diesel/fx/holiday signals.

---

## 6. Commands / Run Instructions

```powershell
# Run API
uv run uvicorn api.main:app --reload

# Run autopilot daemon
uv run python -m scheduler.databricks_autopilot

# Run Streamlit
uv run streamlit run ui/app.py

# Tests
uv run pytest api/tests/
```

---

## 7. Known Issues / Gotchas

1. **Competitor scraper** times out on sastaticket (~2 min, "site structure may have changed"). Autopilot tolerates it.
2. **Dependency-mismatch warning** from MLflow is harmless.
3. **Windows console** can't print emoji — keep prints ASCII.
4. **Playwright** must stay pinned `==1.61.0` (matches cached browsers `chromium-1228`).
5. **`global_changed`/delta logic** already fixed; if re-testing, first `check_for_changes()` call is the baseline (always "changed").
6. PowerShell quoting: f-strings with `:` inside `-c "..."` break — use temp `.py` scripts instead.
7. Never commit the `.env` token to git.
