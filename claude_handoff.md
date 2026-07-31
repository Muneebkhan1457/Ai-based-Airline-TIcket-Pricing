# PIA-Style AI Dynamic Pricing MVP — Complete Handoff Document (Updated)

**Purpose:** Full context-transfer document for continuing this project in a new AI session. Read this first — it captures everything built, every bug found and fixed, every decision made, and exactly what to do next.

**Project root:** `C:\Users\pc\Desktop\data`
**GitHub:** https://github.com/Muneebkhan1457/Ai-based-Airline-TIcket-Pricing
**Python env:** `myenv` (Python 3.11, activated via `.\myenv\Scripts\Activate.ps1`), also `uv` used in some sessions
**Jupyter kernel:** "Python (myenv)", used inside VS Code's notebook viewer

---

## 1. Project Overview

An MVP demo of an AI-driven dynamic ticket pricing system for a PIA-style Pakistani airline, inspired by Delta Airlines' collaboration with Fetcherr (their "Large Market Model" approach). Core idea: ingest internal airline data + external market data (fuel, competitor fares, FX, holidays), train a demand model, and use it to recommend revenue-maximizing prices that update when external factors change.

**Guiding principle:** Use real scraped/API data wherever possible; synthetic data only where real data isn't available — and when synthetic, be honest about it rather than fabricating fake realism.

---

## 2. Folder Structure (current)

```
C:\Users\pc\Desktop\data
├── pia-ai-pricing-mvp-final (1).md        ← early spec doc
├── PIA_AI_Pricing_System_Roadmap.md       ← phase-by-phase roadmap (Phases 1-8)
├── Data_load\                              ← all data collection + storage
│   ├── flight.db                           ← SQLite: flights (15,000 rows), external_signals (24 rows)
│   ├── verify_db.py                        ← full DB audit script
│   ├── etl\ (load_competitor_prices.py, load_fx_rate.py, load_holidays.py,
│   │         load_internal_data.py, load_to_db.py)
│   ├── internal\ (prepare_internal_data.py, generated\flights_internal.csv)
│   ├── raw\ (competitor_prices_*.json, fuel_price_*.json, fx_rate_*.json)
│   ├── scrapers\ (fetch_fx_rate.py, scrape_competitor_prices.py [Playwright], scrap_fuel_price.py)
│   └── tests\ (test_competitor_etl.py, test_etl.py — both passing)
└── models\
    ├── prepare_dataset.py                  ← joins flights + external_signals → training_dataset.csv
    ├── training_dataset.csv                ← 15,000 rows, 18 columns (see section 5)
    ├── train_demand_model.ipynb            ← notebook where EDA + training happened
    ├── demand_model.pkl                    ← trained XGBoost model (see section 6 — NEEDS RETRAINING, see section 7)
    └── feature_columns.pkl                 ← saved column order for the trained model
```

**Critical path convention:** every script uses `Path(__file__).resolve()`-based paths, never cwd-relative paths. This was a hard-learned fix after repeatedly creating duplicate empty databases early on.

---

## 3. Data Layer (Phase 1) — Complete

| Data | Rows | Source |
|---|---|---|
| Internal flights | 15,000 (sampled from 300,261 generated) | Kaggle `shubhambathwal/flight-price-prediction` (India), transformed to PIA-style routes + PKR pricing |
| Fuel price | 2 (petrol, diesel) | Real, scraped from ograprices.com (OGRA has no official API) |
| Competitor price | 6 (3 fares × 2 routes) | Real, scraped from Sastaticket.pk via Playwright (only KHI-LHE and KHI-ISB have real data) |
| FX rate | 1 | Real, free API (open.er-api.com) |
| Holidays | 15 | Real, official 2026 Pakistan Cabinet Division calendar |

**Routes covered:** KHI-LHE, KHI-ISB, KHI-DXB (international), LHE-ISB, KHI-PEW.

**Key gotchas learned in this phase** (in case similar bugs recur):
- SQLite `NULL != NULL` even under `UNIQUE` constraints — use `"GLOBAL"` sentinel, not `None`, for non-route-specific signals.
- `INSERT OR IGNORE` silently swallows NOT-NULL constraint failures too, not just duplicate-key violations — caused a silent fuel-price data-loss bug earlier (wrong JSON key name `date` vs `scraped_date`).
- `page.wait_for_load_state("networkidle")` is unreliable on modern JS-heavy sites (never truly idle) — wait for a specific result-element selector instead. This fixed repeated Playwright timeouts.
- No free/public API exists for Pakistani fuel prices or competitor airline fares — both required scraping (fuel: static HTML + BeautifulSoup; competitor: Playwright, built via `playwright codegen`).

---

## 4. Feature Engineering (`models/prepare_dataset.py`) — Multiple Rounds of Fixes

This script joins `flights` + `external_signals` into `training_dataset.csv`. It went through **two major rounds of bug-fixing**:

### Round 1 — Original bugs (fixed)
- `departure_date` didn't exist in `flights` table; synthesized as `reference_date + days_to_departure`.
- Duplicate temporal-feature computation blocks; consolidated.
- Broken `__main__` guard; fixed.

### Round 2 — Data-quality/honesty bugs (found via investigation, then fixed)
1. **Demand had zero relationship with price** (correlation 0.006) — because `booked_seats` was originally `random.randint(20, 175)` in `Data_load/internal/prepare_internal_data.py`, completely independent of price. **Fixed** by tying `booked_seats` inversely to `price_percentile` with noise — but see Section 7, this fix was itself too strong (see below).
2. **Competitor price feature was ~99% fabricated** — a fallback formula (`price*0.95`/`price*1.02`) was used for the ~60% of rows without real competitor data, making `price_vs_competitor_ratio` a near-constant value. **Fixed**: real values kept only for KHI-LHE/KHI-ISB; all other routes get `NaN` (not fabricated), plus a new boolean column `competitor_data_is_real`.
3. **Fuel/FX prices used a fake sinusoidal trend** (`base ± 5·sin(2π·days/365)`) invented from a single real snapshot, falsely implying real historical variation. **Fixed**: replaced with simple per-row random noise (±10 PKR for petrol, ±3% for diesel/USD-PKR), documented in code as synthetic.
4. **Holiday window was always 0%** — `departure_date` was synthesized from a `2024-01-01` reference while real holiday data is dated 2026 (no overlap). **Fixed**: reference date changed to `2026-07-01`; holiday window now correctly ~13.18% of rows.

**A separate bug found during EDA (also fixed):** `get_competitor_stats_by_route()` was looking up keys like `competitor_min_price_economy` (class-specific), but the database actually stores signal types as `competitor_price_1`, `competitor_price_2`, `competitor_price_3` (numbered, route-level only, not class-specific — because real competitor scraping never captured class information). Fixed by grouping by route only. After this fix, correlation improved from -0.27 to **-0.41**.

**All fixes verified** via an 8-point verification pass: correlation, competitor coverage counts, macro-signal variation stats, holiday percentage, test suite pass, DB row-count integrity, CSV shape, folder tree — all confirmed correct.

---

## 5. Current `training_dataset.csv` Schema (18 columns before encoding)

Dropped before training (5 columns, all either target-leakage or zero-variance):
```python
COLS_TO_DROP = ['id', 'total_seats', 'booked_seats', 'remaining_seats', 'booking_date']
```
- `booked_seats`/`remaining_seats`: direct algebraic components of the target (`demand_ratio = booked_seats/total_seats`) — including them lets the model "cheat" via pure arithmetic instead of learning real relationships.
- `total_seats`: always 180, zero variance.
- `booking_date`: always the same date (`2026-07-01`) — a mathematical identity, since `booking_date = departure_date - days_to_departure = (reference_date + days_to_departure) - days_to_departure = reference_date`, always constant.

**Remaining 18 columns**, classified:

| Type | Columns |
|---|---|
| Categorical (needs one-hot encoding) | `route` (5 values), `flight_class` (2 values) |
| Binary (use as-is) | `is_weekend`, `is_holiday_window`, `competitor_data_is_real`, `is_international` |
| Numerical (use as-is) | `days_to_departure`, `current_price`, `base_fare`, `time_of_day`, `day_of_week`, `petrol_price`, `diesel_price`, `usd_to_pkr`, `competitor_min_price` (NaN for ~60% of rows), `competitor_avg_price` (NaN for ~60%), `price_vs_competitor_ratio` (NaN for ~60%) |
| Target | `demand_ratio` (booked_seats/total_seats, range 0-1) |

**NaN handling:** competitor columns' NaN values are deliberately kept as true `NaN` (not filled with 0) so XGBoost's native missing-value handling can learn optimal split directions — filling with 0 would falsely imply "competitor price is 0 PKR," which is misleading.

**Outlier investigation (thorough, all resolved as non-issues):** IQR-based outlier detection on the whole dataset flagged many "outliers" in `current_price`, `base_fare`, and `price_vs_competitor_ratio`. Investigation showed these were entirely explained by legitimate sub-population mixing:
- `current_price`: 0 outliers once grouped by `(flight_class, is_international)`.
- `base_fare`: 0 outliers once grouped by `(route, flight_class)` (it's a constant per that exact group by design).
- `price_vs_competitor_ratio`: 0 outliers once grouped by `flight_class`.

**Conclusion: no rows need removal.** The dataset is clean; "outliers" were a statistical-check granularity artifact, not bad data.

---

## 6. Model Training — First Attempt (result flagged as unrealistic, needs redo)

Using `xgb.XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9)` on the one-hot-encoded 22-column feature matrix (15,000 rows, 80/20 split):

```
RMSE: 0.0561
R²:   0.9588
```

**Top feature importances:**
```
current_price        0.455
is_international     0.281
base_fare             0.193
flight_class_Business 0.016
price_vs_competitor_ratio 0.015
(everything else: ~1% or less each)
```

### Why this R² is a problem (important — read before continuing)

`R²=0.96` is **unrealistically high** for a demand model — real-world demand prediction typically achieves R² in the 0.2-0.5 range. Investigation revealed this is **not classic column-leakage** (no forbidden column was included), but a subtler issue: the synthetic demand-generation formula in `prepare_internal_data.py` is:

```python
booked_seats = (1 - price_percentile) * 180 * random.uniform(0.85, 1.15)
```

Since `current_price` is itself derived from `price_percentile` via a clean, near-deterministic percentile-to-PKR mapping (per class/international-status), `current_price` + `flight_class` + `is_international` together let XGBoost almost perfectly **reverse-engineer the generating formula itself**, rather than learning a realistically noisy real-world relationship. The ±15% noise wasn't enough to prevent this, because tree-based models are very good at learning clean monotonic/rank-based relationships even when the raw Pearson correlation looks moderate (-0.41).

**This confirms the pipeline architecture works correctly end-to-end** (price → demand flows through the system as designed), but the specific R²=0.96 number should NOT be presented as a validated real-world accuracy figure — it reflects synthetic-data simplicity, not genuine predictive skill on messy real-world demand.

---

## 7. IMMEDIATE NEXT STEP (in progress, not yet completed)

**Decision made:** make the demand-generation formula more realistic by blending the price signal with genuine independent randomness (50/50), so the price→demand relationship is real but appropriately noisy — closer to how real-world demand actually behaves (many factors besides price affect bookings).

**New formula to implement in `Data_load/internal/prepare_internal_data.py`** (replacing the current one-liner):

```python
price_signal = 1 - price_percentile  # 0 to 1, higher when price is lower
random_noise = random.random()        # 0 to 1, completely independent of price

# 50% price-driven, 50% pure randomness — keeps demand meaningfully
# but not perfectly tied to price.
booking_probability = 0.5 * price_signal + 0.5 * random_noise
booked_seats = int(max(20, min(175, booking_probability * 180)))
```

**After this change, the full regeneration pipeline must run again, in order:**
1. `Data_load/internal/prepare_internal_data.py` (regenerates `flights_internal.csv`)
2. Clear the `flights` table, then re-run `Data_load/etl/load_internal_data.py` (repopulates 15,000-row sample)
3. `models/prepare_dataset.py` (regenerates `training_dataset.csv` with the new demand values)
4. **Check the new correlation** between `current_price` and `demand_ratio` — expected to land somewhere around **-0.15 to -0.35** (a moderate, realistic negative relationship — not near 0, not near -1).
5. Re-run the training notebook cells (one-hot encode → train/test split → XGBoost train → evaluate). **Expected new R² should be noticeably lower than 0.9588 — something like 0.25-0.45 would indicate a healthy, realistic model.** If R² is still above ~0.7, the blend may need even more randomness (e.g. 30% price / 70% random).
6. Re-check feature importance — `current_price` should still be meaningfully important but not dominate ~45%+ alone; other features (competitor, fuel, holiday) should contribute a more visible (though still smaller) share than before.
7. Re-run the full test suite (`pytest Data_load/tests`) and `Data_load/verify_db.py` to confirm nothing else broke.
8. Save the new model: `joblib.dump(model, 'demand_model.pkl')` and `joblib.dump(list(X.columns), 'feature_columns.pkl')` (overwriting the old, invalidated model from Section 6).

---

## 8. What Comes After That (Phases 4-8, not yet started)

Per `PIA_AI_Pricing_System_Roadmap.md`:

- **Phase 4 — Pricing Optimization Engine** (`pricing_engine/`): grid-search over candidate prices, `Expected Revenue(P) = P × predicted_demand(P)`, plus guardrails (price floor/ceiling relative to base fare, competitor floor/ceiling, urgency modifier for low days-to-departure + high remaining capacity). **This is where `remaining_seats`/inventory scarcity logic belongs** — it was correctly excluded from the demand model (leakage) but is a legitimate business-rule input at pricing-decision time.
- **Phase 5 — Autonomous Scheduler** (`scheduler/`): periodic re-scraping (fuel ~15 days, competitor 2-3×/day, FX hourly) + delta-check trigger logic — recalculates price for a route only when a relevant external factor actually changed, using the FULL current feature set (not just the changed factor) for the recalculation itself.
- **Phase 6 — FastAPI service layer** (`api/`): single service touching the DB; endpoints for price recommendation, batch repricing, manual ETL trigger.
- **Phase 7 — Streamlit dashboard** (`ui/`): calls the API only (never touches the DB directly — deliberate separation of concerns); shows live pricing, elasticity simulator, market signal monitor.
- **Phase 8 — Backtesting/simulation**: compare static vs AI dynamic pricing revenue uplift over simulated flights.

---

## 9. Key Lessons To Carry Forward

1. Always use `Path(__file__).resolve()`-based paths, never cwd-relative.
2. SQLite treats `NULL != NULL` even under `UNIQUE` — use a sentinel string for "no route" signals.
3. `INSERT OR IGNORE` hides NOT-NULL failures too — use plain `INSERT` while debugging.
4. Don't fabricate fake realism (sinusoidal trends, formula-based fallbacks) to paper over data gaps — prefer honest NaN/constants over invented patterns; it's more maintainable and avoids misleading downstream models.
5. A suspiciously high R² is a signal to investigate feature importance and the target-generation logic, not something to celebrate uncritically — especially with synthetic data where the generating formula can be "too clean" for a target column even without classic leakage.
6. Grouped statistical checks (outlier detection, correlation) matter — checking at the wrong granularity (e.g. across mixed classes/routes) produces false alarms.
