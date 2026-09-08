# PIA Dynamic Pricing — Teacher Demo Script

**Purpose:** A complete walkthrough you can literally read from during the demo — what to say, what to run, what to expect.

---

## Before You Start — Pre-Demo Checklist

Run these the night before (or an hour before) to make sure everything is warm and ready:

```powershell
cd C:\Users\pc\Desktop\data

# Confirm local DB is healthy
uv run python Data_load/verify_db.py

# Confirm tests pass (both local and API)
uv run pytest Data_load/tests api/tests -v
```

Expect: DB row counts look normal, all tests green. If anything fails, fix it before the demo — don't discover it live.

Also do ONE Databricks warm-up query beforehand (open the workspace, run any cell) — Databricks SQL Warehouses "cold start" and can take 3-6 minutes to spin up if idle. You don't want your teacher waiting on that live.

---

## Part 1 — What To Say (The Pitch, ~2 minutes)

> "This is an AI-based dynamic ticket pricing system for a PIA-style airline, inspired by how Delta Airlines uses an AI engine (built by a company called Fetcherr) to adjust fares in real time based on demand, competitor prices, and fuel costs — instead of using fixed fare buckets.
>
> I built the full pipeline myself: scraping real fuel prices and competitor fares, training a machine learning model that predicts booking demand at any given price, and an optimization engine that picks the price that maximizes expected revenue — subject to business rules like price floors and competitor limits.
>
> I first built and fully tested this locally, then migrated the model and data storage to Databricks with MLflow, to make it more production-like — versioned models, cloud-hosted data, and a proper experiment tracking system."

---

## Part 2 — Start the System (Commands)

**Terminal 1 — Start the API:**
```powershell
cd C:\Users\pc\Desktop\data
uv run uvicorn api.main:app --port 8000
```
Wait for: `Application startup complete.`

**Terminal 2 — Start the Dashboard:**
```powershell
cd C:\Users\pc\Desktop\data
uv run streamlit run ui/app.py
```
This opens a browser tab at `http://localhost:8501`.

> Say: "The dashboard only talks to my API over HTTP — it never touches the database directly. The API is the one that talks to Databricks."

---

## Part 3 — Live Demo Walkthrough (What To Click, What To Say)

### Step 1 — System Status (Sidebar)
Point at the sidebar. Say:
> "This confirms three things are alive: the API, the database connection to Databricks, and that the trained model loaded successfully."

### Step 2 — Get a Price Recommendation
Set: Route = `KHI-LHE`, Class = `Economy`, Days to Departure = `10`, Total Seats = `180`, Remaining Seats = `90`.
Click **"Get Recommended Price"**.

> Say while it loads: "Right now, this call is going to my API, which queries Databricks for the real base fare and real competitor prices for this route, loads the trained model from the MLflow Model Registry, then tests over 100 candidate prices — asking the model 'if I charge this price, what demand do you predict?' — and picks whichever price gives the highest expected revenue."

Expected result: price around 10,000-11,000 PKR, with a caption "Priced with real competitor data" (because KHI-LHE has real scraped competitor fares).

**Follow-up — change the route to KHI-PEW, click again:**
> "Notice the price is much higher now, and it says 'No real competitor data.' That's because only 2 of our 5 routes have real scraped competitor prices — for the rest, the pricing relies more heavily on the base fare and business guardrails alone."

### Step 3 — Elasticity Simulator Tab
Click the tab, select KHI-LHE / Economy, click **"Run Simulation"**.
> "This shows the actual price-demand curve the model learned. As price goes up, predicted demand goes down — this has to be strictly decreasing, because I explicitly forced this using something called monotone constraints during training. I'll explain why in a second."

**If asked "why did you need to force this":**
> "Early on, my model was trained on features that accidentally let it 'cheat' — and even after I fixed that, it briefly predicted a nonsensical spike where demand went UP at a very high price, just from noise in the data. That would have caused the pricing engine to recommend absurd fares. Monotone constraints mathematically force the model to always respect the real-world rule that higher price means lower or equal demand."

### Step 4 — Manual ETL Refresh (Sidebar)
Click **"Trigger Manual ETL Refresh"**.
> "This runs my three scrapers live right now — one for OGRA fuel prices, one for competitor fares from a travel site using a headless browser, and one for the USD-PKR exchange rate — and pushes anything new into the database."

*(Note: the competitor scraper sometimes times out because the target site's page structure changes or loads slowly — mention this proactively: "This one occasionally times out because the site I scrape is JS-heavy; the system handles that gracefully and just keeps the last known values.")*

### Step 5 — Batch Reprice (Main Button)
Click **"Reprice ALL Routes (Batch)"**.
> "This runs the full pricing cycle for all 5 routes and both classes — 10 recommendations at once — and logs every one of them to Databricks so there's a permanent history of pricing decisions."

Wait ~1-3 minutes (there's an info message explaining why). A table appears afterward with all 10 results.

### Step 6 — Market Signals Tab
Click it, show the real signal history table (fuel prices over time, FX rates, holidays).
> "This is pulling directly from the Databricks external_signals table — real historical data, not synthetic."

---

## Part 4 — Show the Databricks Side (Switch to Browser Tab)

Open the Databricks workspace. Show:

1. **Catalog Explorer → airline_daw → pia_pricing** — show the 3 tables (`flights`, `external_signals`, `price_history`), click one, show row counts.
2. **Machine Learning → Models → pia-demand-model** — show version history (say: "this went through 8 versions — including catching and fixing a bug where an earlier version had accidentally perfect accuracy, which is actually a red flag, not a good sign, since it meant the model was cheating rather than learning").
3. Click into the current production version → show the **Metrics** panel (R² ≈ 0.44-0.48, RMSE ≈ 0.14-0.15).

> Say: "An R² around 0.45 means the model explains about 45% of the variance in booking demand — which is realistic for real-world travel demand, where a lot of randomness exists beyond just price. A perfect R² of 1.0 would actually be suspicious, not impressive — it usually means the model is leaking the answer."

---

## Part 5 — Key Numbers To Have Ready (If Asked)

| Question | Answer |
|---|---|
| How much data? | 15,000 flight records, 38 real external signal records (fuel, FX, competitor, holidays) |
| Model performance? | R² ≈ 0.45-0.48, RMSE ≈ 0.14-0.15 |
| How many model versions? | 8 (including catching and fixing a target-leakage bug and switching model type) |
| Automated tests? | 11 passing (2 data pipeline + 9 API) |
| Backtest revenue uplift? | Roughly +19% to +24% (varies slightly run to run since some signal noise isn't seeded) — **say clearly this is a simulation using the model's predicted demand, not a proven real-world A/B test result** |
| Real vs synthetic data? | Fuel, FX, and holiday data are 100% real (scraped/API). Competitor fares are real for 2 of 5 routes (limited by scraping access). Internal flight records are derived from a real Kaggle dataset, transformed to PIA-style routes and PKR pricing. |

---

## Part 6 — Honest Limitations (Mention Proactively — It Builds Credibility)

> "A few honest limitations I'd flag myself: the backtest is a simulation, not a real A/B test, so the revenue uplift number is what the model believes it would achieve, not a guarantee. Competitor pricing is only real for 2 of the 5 routes because of scraping access limits. And the fuel/FX price variation used in training is synthetic noise around one real snapshot, not a true historical time series yet — that would improve once the system runs continuously and accumulates real day-over-day data."

---

## Part 7 — Shutdown (After the Demo)

```powershell
# In each terminal, press:
Ctrl+C
```
Stop both the API and Streamlit processes when done — don't leave them running.

---

## Quick Reference — All Commands in One Place

```powershell
cd C:\Users\pc\Desktop\data

# Pre-demo checks
uv run python Data_load/verify_db.py
uv run pytest Data_load/tests api/tests -v

# Start the demo (2 terminals)
uv run uvicorn api.main:app --port 8000        # Terminal 1
uv run streamlit run ui/app.py                  # Terminal 2

# Optional — show these are real if asked to prove it
uv run python backtest/simulate.py              # re-run backtest live
uv run python -m scheduler.databricks_autopilot # run one autopilot cycle (Ctrl+C after first cycle)
```
