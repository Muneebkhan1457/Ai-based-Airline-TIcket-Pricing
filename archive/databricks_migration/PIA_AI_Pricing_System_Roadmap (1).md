# PIA AI-Powered Dynamic Ticket Pricing System (Fetcherr Clone MVP)
## End-to-End Technical Documentation & Execution Roadmap

---

## 1. Executive Summary & Architecture Overview

This project builds an AI-driven high-frequency dynamic ticket pricing system for **Pakistan International Airlines (PIA)**, inspired by the architecture and capabilities of **Fetcherr's AI Market Engine**. 

Traditional airline Revenue Management Systems (RMS) rely on static fare buckets and manual analyst overrides. This system implements **continuous, autonomous dynamic pricing** using real-time market signals (fuel prices, exchange rates, holiday calendars, competitor fares) alongside historical booking demand patterns.

### Core Architecture Layers:
1. **Data & Ingestion Layer (`Data_load/`)**: Automated scraping, ETL, raw data ingestion, and SQLite database storage for internal flight records and external macroeconomic/competitor market signals.
2. **Intelligence & ML Layer (`models/`)**: XGBoost-based demand prediction engine modeling price elasticity, lead times, holiday impacts, and competitor dynamics.
3. **Dynamic Pricing Optimization Engine (`pricing_engine/`)**: Revenue-maximizing optimization function subject to dynamic inventory guardrails, price elasticity bounds, and competitor floor/ceiling rules.
4. **Autonomous Scheduler & Event-Driven Delta Trigger (`scheduler/`)**: 24/7 background process that periodically scrapes new market signals, detects factor changes (delta check), and conditionally triggers the ML model and price optimizer only when actual market factor changes occur.
5. **Service & API Layer (`api/`)**: High-performance FastAPI endpoints exposing real-time dynamic pricing, batch repricing, and signal update triggers.
6. **Dashboard & Control Center (`ui/`)**: Streamlit / Next.js revenue management cockpit allowing interactive simulation, real-time pricing strategy overrides, and market signal monitoring.

---

## 2. Project Status & Completed Work (Phases 1 & 2)

### Status: Data Layer Complete & Verified (100%)

```
C:\Users\pc\Desktop\data\
├── pia-ai-pricing-mvp-final (1).md        # Initial Project Specification
└── Data_load/                              # Standardized Data Pipeline Directory
    ├── flight.db                           # Primary SQLite Database
    ├── verify_db.py                        # DB Sanity & Verification Suite
    ├── etl/                                # ETL Pipeline Scripts
    │   ├── load_competitor_prices.py
    │   ├── load_fx_rate.py
    │   ├── load_holidays.py
    │   ├── load_internal_data.py
    │   └── load_to_db.py
    ├── internal/                           # Synthetic Data Generation
    │   ├── prepare_internal_data.py
    │   └── generated/
    ├── raw/                                # Raw API/Scraper Responses JSON
    │   ├── competitor_prices_2026-07-28.json
    │   ├── fuel_price_2026-07-27.json
    │   └── fx_rate_2026-07-28.json
    ├── scrapers/                           # Automated External Data Scrapers
    │   ├── fetch_fx_rate.py
    │   ├── scrape_competitor_prices.py
    │   └── scrap_fuel_price.py
    └── tests/                              # Automated Test Suite (Pytest)
        ├── test_competitor_etl.py
        └── test_etl.py
```

### Completed Key Milestones:
1. **Synthetic Internal Flight Generation (`internal/`)**:
   - Generated **15,000 synthetic historical flight booking records** in `flight.db` (`flights` table).
   - Primary routes: `KHI-LHE` (Karachi-Lahore) and `KHI-ISB` (Karachi-Islamabad).
   - Schema fields: `flight_id`, `route`, `departure_date`, `departure_time`, `total_seats`, `booked_seats`, `base_fare`, `class` (Economy/Business), `days_to_departure`.

2. **External Market Signal Collectors (`scrapers/` & `etl/`)**:
   - **Fuel Price Scraper**: Fetches real-time OGRA petrol/diesel rates (`petrol_price`: ~335.18 PKR/L, `diesel_price`: ~383.46 PKR/L).
   - **Competitor Fare Scraper**: Scrapes real-time fares from Sastaticket for competitors (Airblue, Serene Air, Fly Jinnah) across target routes.
   - **FX Rate Integrator**: Open Exchange Rates API integration for USD to PKR rate (~277.86 PKR/USD).
   - **Holiday Calendar**: Ingested full 2026 Pakistan Official Calendar (15 national/religious holidays).

3. **Database & ETL Architecture (`flight.db`)**:
   - Consolidated table `external_signals` storing time-stamped market signals with full provenance tracking.
   - Cleaned, validated, and verified: 24 active external signal records + 15,000 internal flight records.
   - 100% test pass rate with `pytest` suite.

4. **Directory Organization (`Data_load/`)**:
   - Clean separation of concerns with all ingestion, ETL, tests, and storage isolated in `Data_load/`.
---

## 3. Detailed Step-by-Step Remaining Roadmap

---

### Phase 3: Demand Modeling & ML Intelligence (`models/`)
**Objective**: Train a machine learning model to accurately predict ticket demand (Load Factor / Booked Seats Ratio) given flight parameters and real-time external market signals.

#### Step 3.1: Directory & Setup
* Create `models/` folder at project root level (`C:\Users\pc\Desktop\data\models`).

#### Step 3.2: Feature Engineering & Dataset Preparation (`models/prepare_dataset.py`)
* Extract features from `Data_load/flight.db`:
  - **Internal Features**: `route`, `cabin_class`, `days_to_departure`, `base_fare`, `departure_time_of_day` (Morning, Afternoon, Evening, Night), `day_of_week`, `is_weekend`.
  - **External Features**: `fuel_price` (nearest recorded date), `usd_pkr_rate`, `is_holiday_window` (1-3 days prior/after official holiday), `competitor_min_price`, `competitor_avg_price`.
  - **Target Variable ($y$)**: `demand_ratio = booked_seats / total_seats` (range 0.0 to 1.0).

#### Step 3.3: Model Training Script (`models/train_demand_model.py`)
* Tech Stack: `XGBoostRegressor` / `LightGBM`, `scikit-learn`, `joblib`.
* Workflow:
  1. Train-Test Split (80/20 chronological or stratified split).
  2. Categorical Encoding (One-Hot Encoding for routes/classes/time slots).
  3. Feature Scaling for continuous variables.
  4. Hyperparameter Optimization using `GridSearchCV` or `Optuna`.
  5. Save model binary (`models/demand_model.pkl`) and preprocessor transformers (`models/preprocessor.pkl`).

#### Step 3.4: Model Evaluation & Validation (`models/evaluate_model.py`)
* Metrics: Root Mean Squared Error (RMSE), Mean Absolute Error (MAE), $R^2$ Score.
* **Price Elasticity Verification**: Validate that predicted demand decreases monotonically as base fare increases ($rac{\partial \text{Demand}}{\partial \text{Price}} < 0$).

---

### Phase 4: Dynamic Pricing & Optimization Engine (`pricing_engine/`)
**Objective**: Develop the core mathematical optimization module that recommends optimal prices to maximize expected flight revenue.

#### Step 4.1: Architecture & Directory (`pricing_engine/`)
* Directory layout:
  ```
  pricing_engine/
  ├── __init__.py
  ├── elasticity.py          # Price elasticity simulator
  ├── optimizer.py           # Revenue maximization algorithm
  └── guardrails.py          # Business rules & boundary checks
  ```

#### Step 4.2: Expected Revenue Function Definition
For a given flight $i$ at $d$ days to departure, expected revenue at price $P$ is:
$$\text{Expected Revenue}(P) = P \times \min\left(\text{Total Seats} - \text{Booked Seats}, \hat{y}(P) \times \text{Total Seats}\right)$$
where $\hat{y}(P)$ is predicted load factor from `demand_model.pkl`.

#### Step 4.3: Optimization Algorithm (`pricing_engine/optimizer.py`)
* Evaluate candidate prices $P \in [P_{\min}, P_{\max}]$ with step size $\Delta P = 250\text{ PKR}$.
* Identify $P^* = \arg\max_P \text{Expected Revenue}(P)$.

#### Step 4.4: Guardrails & Constraints (`pricing_engine/guardrails.py`)
* **Price Bounds**: Absolute floor ($P_{\min} = 0.7 \times \text{Base Fare}$) and ceiling ($P_{\max} = 2.5 \times \text{Base Fare}$).
* **Competitor Dynamic Floor/Ceiling**: Prevent pricing more than $15\%$ higher than competitor average unless flight capacity exceeds $85\%$.
* **Urgency Modifier**: Escalation factor when `days_to_departure` $< 3$ and remaining capacity $> 30\%$.

---

### Phase 5: Autonomous Background Scheduler & Event-Driven Delta Trigger (`scheduler/`)
**Objective**: Enable 100% hands-free autonomous operation via periodic scraping, delta detection, and conditional repricing execution.

#### Step 5.1: Directory & Setup (`scheduler/`)
* Directory layout:
  ```
  scheduler/
  ├── __init__.py
  ├── jobs.py                # Wrapper jobs for scraping, ETL & pricing
  ├── delta_check.py         # Market factor change detection logic
  └── run_autopilot.py       # Background daemon (APScheduler)
  ```

#### Step 5.2: Event-Driven Delta Checking Workflow
Instead of unconditionally re-running heavy ML model inference, the system follows a smart, resource-efficient event loop:

$$\text{Autonomous Clock Trigger} \longrightarrow \text{Scrape Latest Factors} \longrightarrow \text{Delta Check vs DB}$$

$$\text{Delta Check} = \begin{cases} \mathbf{\text{CHANGE DETECTED:}} & \text{Save Signals} \longrightarrow \text{Run ML Model} \longrightarrow \text{Optimize Price} \longrightarrow \text{Update DB/API} \\ \mathbf{\text{NO CHANGE:}} & \text{Do NOTHING (Keep current prices intact, skip ML model)} \end{cases}$$

#### Step 5.3: Core Logic (`scheduler/delta_check.py` & `run_autopilot.py`)
1. **Periodic Execution**: `APScheduler` wakes up automatically every $N$ minutes/hours (e.g., 30 minutes).
2. **Factor Extraction**: Scrapers fetch current fuel prices, exchange rates, and competitor fares.
3. **Delta Comparison**:
   - Compare `new_fuel_price` vs `latest_db_fuel_price`.
   - Compare `new_fx_rate` vs `latest_db_fx_rate`.
   - Compare `new_competitor_fares` vs `latest_db_competitor_fares`.
4. **Conditional Triggering**:
   - If **ANY factor has changed**: Save new signals to `flight.db`, execute `train_demand_model / predict`, run `pricing_engine/optimizer.py`, and write updated prices to `flight.db`.
   - If **NO factors changed**: Log `"No market changes detected. Prices remain unchanged."` and sleep until next interval.

---

### Phase 6: REST API Layer (`api/`)
**Objective**: Serve dynamic pricing recommendations and accept external trigger signals via a production-grade FastAPI web service.

#### Step 6.1: Directory & Structure
```
api/
├── main.py                # FastAPI app instance & routes
├── schemas.py             # Pydantic request/response models
├── services.py            # Business logic linking ML & pricing engine
└── tests/
    └── test_api.py
```

#### Step 6.2: API Endpoints Specification
1. `GET /health`: System operational status and database connection check.
2. `POST /pricing/recommend`: Accepts `flight_id`, `route`, `days_to_departure`, `seats_remaining`, returns `recommended_price`, `expected_revenue`, `demand_forecast`, and `price_breakdown_factors`.
3. `POST /pricing/batch-reprice`: Batch processes all upcoming scheduled flights and returns updated price matrix.
4. `POST /signals/trigger-etl`: Endpoint to manually or programmatically trigger scrapers, delta checks, and recalculate fares upon external market shifts.

---

### Phase 7: Revenue Management Cockpit UI (`ui/`)
**Objective**: Build a clean interactive user interface using Streamlit or Next.js for revenue managers.

#### Step 7.1: Key Dashboard Views
1. **Live Pricing Dashboard**:
   - Table of active flights with current fare vs AI-recommended dynamic fare.
   - Expected revenue gain comparison (Static Pricing vs AI Dynamic Pricing).
   - One-click "Approve All" / "Manual Override" controls.
2. **Elasticity & Scenario Simulator**:
   - Interactive slider for price adjustments showing real-time impact on predicted demand curve and revenue curve.
3. **Market Signal Monitor & Autopilot Log**:
   - Live trends for OGRA fuel prices, USD/PKR exchange rates, and competitor pricing on `KHI-LHE` / `KHI-ISB`.
   - Autopilot execution status log showing when market changes occurred and triggered automatic repricing.

---

### Phase 8: Simulation, Validation & End-to-End Integration
**Objective**: Run complete end-to-end integration tests and market revenue simulation.

#### Step 8.1: Historical Backtesting / Revenue Uplift Simulation
* Compare static legacy pricing strategy vs dynamic AI strategy over 1,000 simulated flights.
* Compute total revenue uplift percentage ($\% \Delta \text{Revenue}$).

---

## 4. Summary of File & Folder Target Structure

```
C:\Users\pc\Desktop\data\
├── pia-ai-pricing-mvp-final (1).md
├── PIA_AI_Pricing_System_Roadmap.md         # THIS COMPREHENSIVE ROADMAP
├── Data_load/                               # Data & Ingestion (COMPLETE)
│   ├── flight.db
│   ├── verify_db.py
│   ├── etl/
│   ├── internal/
│   ├── raw/
│   ├── scrapers/
│   └── tests/
├── models/                                  # Machine Learning (NEXT STEP)
│   ├── prepare_dataset.py
│   ├── train_demand_model.py
│   ├── evaluate_model.py
│   ├── demand_model.pkl
│   └── preprocessor.pkl
├── pricing_engine/                          # Dynamic Optimization Engine
│   ├── elasticity.py
│   ├── optimizer.py
│   └── guardrails.py
├── scheduler/                               # Autonomous Background Scheduler (AUTOPILOT)
│   ├── __init__.py
│   ├── jobs.py
│   ├── delta_check.py
│   └── run_autopilot.py
├── api/                                     # FastAPI Service Layer
│   ├── main.py
│   ├── schemas.py
│   └── services.py
└── ui/                                      # Streamlit Revenue Dashboard
    └── app.py
```
