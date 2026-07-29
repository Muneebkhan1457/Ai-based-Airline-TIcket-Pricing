# AI-Based Dynamic Ticket Pricing System — Final MVP Description

**Project type:** Portfolio / demo project
**Inspired by:** Delta Airlines × Fetcherr (Large Market Model approach)
**Scope:** MVP demo for a PIA-like airline, with real-time multi-factor price updates

---

## 1. Project Overview

This project is a smaller-scale demo of the AI-driven dynamic pricing systems used by real airlines like Delta (via Fetcherr). It ingests internal airline data (bookings, inventory, fares) and external market data (fuel price, competitor fares, FX rate, demand signals), trains a demand forecasting model, and uses that model to recommend the revenue-maximizing ticket price. Prices update automatically whenever any relevant external factor changes — not on a fixed schedule alone.

The goal is not to replicate Fetcherr's production-scale infrastructure, but to demonstrate the same core pattern: **data in → model learns demand → optimization picks the best price → price reacts as conditions change.**

## 2. Problem Statement

Traditional airline pricing relies on static fare buckets and manual analyst adjustments. This system automates that process by continuously learning demand patterns and adjusting prices based on internal and external signals, without a human manually repricing every route.

## 3. Core Features

- Synthetic airline booking/inventory data (PIA-style domestic and international routes)
- Mixed real and synthetic external data feeds
- Demand forecasting model (predicts booking probability given price and context)
- Price optimization engine (selects the price that maximizes expected revenue)
- Day-by-day booking simulation loop (shows how price evolves as a flight approaches departure)
- Multi-factor real-time trigger — any relevant external change (fuel, competitor, FX, demand) triggers recalculation for affected routes, and the model always predicts using the full current feature set, not just the changed factor
- Explainability layer — shows why a given price was recommended
- API + live dashboard

## 4. Data Sources

| Data | Source type | Notes |
|---|---|---|
| Internal bookings, inventory, fares | Synthetic | Generated for PIA-style routes (e.g. Karachi–Lahore, Karachi–Islamabad, Karachi–Dubai) |
| Fuel price | Real, manually tracked | No public OGRA API exists; updated on OGRA's fortnightly revision cycle |
| Competitor pricing | Synthetic | No public API for Pakistani airline fares; generated as randomized variation around own price |
| USD-PKR exchange rate | Real API | Free tier (e.g. exchangerate-api.com, open.er-api.com) |
| Seasonality / holidays | Real | Pakistan holiday calendar (Eid, Hajj season, public holidays) |
| Demand signal | Derived | Computed from the booking simulator's own activity |

## 5. System Architecture (Layers)

```
Data sources layer        → internal + external, real + synthetic
        ↓
Data & storage layer      → SQLite: flights, external_signals, price_history
        ↓
Intelligence layer        → demand model, optimization engine, SHAP explainability
        ↓
Real-time trigger layer   → scheduler detects any signal change
        ↓
Serving layer             → FastAPI + Streamlit dashboard
```

## 6. Real-Time Trigger Logic

The scheduler checks all external signals on an interval (every 5-10 minutes). The trigger condition is an OR across factors: if fuel price, competitor price, FX rate, or demand signal has changed for a route, recalculation fires for that route only — unaffected routes are left untouched.

Important distinction: the trigger only decides *whether* to recalculate. The prediction itself always uses the full current feature set (fuel, competitor, FX, demand, days-to-departure, remaining inventory) together, not just the factor that changed. This lets the model weigh opposing signals — e.g. rising fuel cost pushing price up while a competitor's price drop pushes it down — into one balanced, learned decision, rather than applying rigid if-then rules.

```
Scheduler checks signals → any factor changed? 
    yes → recalculate affected routes using ALL current features → update price_history and flights table
    no  → wait for next interval, recheck
```

## 7. Complete Runtime Flow

**One-time setup:**
1. Generate synthetic data → populate SQLite
2. Train demand model on historical data → save model file
3. Initialize database tables
4. Start FastAPI server
5. Start Streamlit dashboard
6. Start background scheduler

**Continuous runtime loop:**
1. Scheduler checks external signals every 5-10 minutes
2. Compares against last known values per route
3. If any factor changed, recalculates price for affected routes using the full feature set
4. Logs new price to `price_history`, updates `flights` table
5. API and dashboard always serve the latest stored price on demand

## 8. Tech Stack

| Layer | Tool/Library | Purpose |
|---|---|---|
| Language | Python 3.11 | Core development |
| Package management | uv | Environment and dependency management |
| Data handling | pandas, numpy | Cleaning, feature engineering |
| Demand model | XGBoost / LightGBM | Predicts booking probability |
| Explainability | SHAP | Explains why a price was chosen |
| Optimization | Custom Python (grid search) | Finds revenue-maximizing price |
| Scheduling / trigger | APScheduler (MVP) → Redis Pub/Sub (stretch) | Detects signal changes, fires recalculation |
| Storage | SQLite | Stores prices, signals, history |
| Backend/serving | FastAPI | Exposes price + explanation via API |
| Dashboard | Streamlit | Live price trends, demand curve, explainability panel |
| External data | Free FX API + manual fuel tracking + synthetic competitor generator | Real-world signal simulation |

## 9. Suggested Project Structure

```
pia-pricing-mvp/
├── data/
│   ├── generate_synthetic_data.py
│   └── flights.db
├── models/
│   ├── train_demand_model.py
│   └── demand_model.pkl
├── core/
│   ├── optimization.py
│   ├── explainability.py
│   └── feature_engineering.py
├── realtime/
│   ├── scheduler.py
│   └── external_signals.py
├── api/
│   └── main.py
├── dashboard/
│   └── app.py
└── pyproject.toml
```

## 10. Out of Scope (for MVP)

- Real production airline data integration
- Full-scale message queue infrastructure (Kafka, etc.)
- Personalized/individual-level pricing
- Multi-region cloud deployment
- Live scraping of competitor booking sites

## 11. Success Criteria

- Model produces sensible, explainable price recommendations
- Simulation shows price adapting over the booking window
- Price recalculates automatically when any relevant external signal changes, using the combined feature set
- Dashboard clearly shows current price, demand curve, and reasoning
