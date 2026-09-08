# PIA Dynamic Pricing — Complete Databricks + MLflow Migration Guide

## 📋 Master Index & Roadmap

Your project is being migrated from **local MVP** → **Databricks + MLflow** with everything post-model-training happening on Databricks.

---

## 🎯 High-Level Flow

```
LOCAL SYSTEM (Your Computer)
├── Phase 0: Export model pkl files after local training
└── Deliver: demand_model.pkl, preprocessor.pkl, training_dataset.csv

        ↓↓↓ HANDOFF ↓↓↓

DATABRICKS (Cloud)
├── Phase 1: Cluster setup
├── Phase 2: Data migration (CSV → Delta tables)
├── Phase 3: Feature engineering
├── Phase 4: Model training with MLflow logging
├── Phase 5: MLflow Model Registry setup
├── Phase 6: Pricing engine on Databricks
├── Phase 7: Autonomous scheduler on Databricks
├── Phase 8: Batch pricing & API endpoints (notebooks)
├── Phase 9: Dashboard (Streamlit on Databricks)
└── Phase 10: Backtesting & revenue simulation
```

---

## 📖 Phase-by-Phase Documentation

| Phase | Document | What Happens | Estimated Time |
|-------|----------|-------------|-----------------|
| **0** | `DATABRICKS_MIGRATION_PHASE0.md` | Account setup, CLI auth, workspace config | 15 min |
| **1** | `DATABRICKS_MIGRATION_PHASE1.md` | Create cluster, install packages, verify MLflow | 10 min |
| **2** | `DATABRICKS_MIGRATION_PHASE2.md` | Export local SQLite → CSV, upload to Databricks, create Delta tables | 10 min |
| **3** | `DATABRICKS_MIGRATION_PHASE3.md` | Feature engineering in Databricks (notebook) | 20 min |
| **4** | `DATABRICKS_MIGRATION_PHASE4.md` | Train XGBoost model with MLflow tracking & logging | 15 min |
| **5** | `DATABRICKS_MIGRATION_PHASE5.md` | MLflow Model Registry, promote to Production (coming soon) | 5 min |
| **6** | `DATABRICKS_MIGRATION_PHASE6.md` | Pricing engine ported to Databricks (coming soon) | 20 min |
| **7** | `DATABRICKS_MIGRATION_PHASE7.md` | Autonomous scheduler & delta triggers (coming soon) | 20 min |
| **8** | `DATABRICKS_MIGRATION_PHASE8.md` | API endpoints as Databricks notebooks (coming soon) | 20 min |
| **9** | `DATABRICKS_MIGRATION_PHASE9.md` | Streamlit dashboard on Databricks (coming soon) | 20 min |
| **10** | `DATABRICKS_MIGRATION_PHASE10.md` | Backtesting & verification (coming soon) | 15 min |

**Total estimated time:** ~2 hours (once you reach Phase 5, rest are parallelizable)

---

## 🚀 Quick Start Checklist

### Before You Begin:
- [ ] Databricks account (free Community Edition)
- [ ] Your local project fully trained with `demand_model.pkl` ready
- [ ] CSV exports of `flights` and `external_signals` tables ready

### Do These Steps IN ORDER:

1. **Phase 0**: Set up Databricks account + CLI
   ```
   Go to: https://community.cloud.databricks.com/login.html
   Complete: DATABRICKS_MIGRATION_PHASE0.md
   ```

2. **Phase 1**: Create cluster
   ```
   Databricks UI → Compute → Create Cluster
   Complete: DATABRICKS_MIGRATION_PHASE1.md
   ```

3. **Phase 2**: Migrate data
   ```
   Export flights.db locally → upload CSVs → create Delta tables
   Complete: DATABRICKS_MIGRATION_PHASE2.md
   ```

4. **Phase 3**: Build feature engineering notebook
   ```
   Create notebook 02_prepare_dataset in Databricks
   Complete: DATABRICKS_MIGRATION_PHASE3.md
   ```

5. **Phase 4**: Train model with MLflow
   ```
   Create notebook 03_train_demand_model in Databricks
   Complete: DATABRICKS_MIGRATION_PHASE4.md
   ```

6. **Remaining phases** (coming next):
   - Phase 5: Model Registry + promotion
   - Phases 6-10: Pricing engine, scheduler, API, dashboard, backtest

---

## 📊 Key Databricks/MLflow Concepts You'll Use

### MLflow Experiments & Runs
- **Experiment**: A project-level container (like a folder) for all model training runs
- **Run**: A single training execution, with params, metrics, and artifacts logged
- **Artifact**: Model binary, config files, evaluation plots saved with a run

**In your case:**
- Experiment path: `/Shared/pia-pricing-migration/demand-model`
- Each training produces one run with hyperparams, metrics, and the trained model

### MLflow Model Registry
- **Versioning**: Each registered model gets version numbers (v1, v2, v3...)
- **Staging**: Versions can be in stages (None → Staging → Production → Archived)
- **Model URI**: `models:/pia-demand-model/Production` — how other code loads the model

**In your case:**
- Register the best training run as `pia-demand-model`
- Promote to "Production" stage
- All downstream code (pricing engine, etc.) loads via this URI

### Delta Tables
- **Databricks-native table format** (built on Parquet, optimized for ACID operations)
- **Versioning**: Every write creates a new version, history trackable
- **Performance**: Optimized for analytical queries

**In your case:**
- `pia_pricing.flights`: Your 15K flight records
- `pia_pricing.external_signals`: Your market signals
- `pia_pricing.training_dataset`: Features ready for model training

---

## 💾 File Organization in Databricks

Once complete, your Databricks workspace will look like:

```
/Users/<your-email>/pia-pricing-migration/
├── 00_verify_packages                    (verification notebook)
├── 01_setup_delta_tables                 (data ingestion)
├── 01b_verify_data_sql                   (SQL verification)
├── 02_prepare_dataset                    (feature engineering)
├── 03_train_demand_model                 (model training + MLflow)
├── 04_pricing_engine                     (optimization logic)
├── 05_scheduler_autopilot                (autonomous delta triggers)
├── 06_batch_pricing_api                  (pricing endpoints)
├── 07_dashboard                          (Streamlit UI)
└── 08_backtest_simulation                (revenue verification)

MLflow Tracking Server (Built-in):
├── Experiment: /Shared/pia-pricing-migration/demand-model
│   └── Run #1: xgboost-monotonic-v1-[timestamp]
│       ├── Params: n_estimators, max_depth, learning_rate, ...
│       ├── Metrics: train_rmse, test_rmse, test_r2, ...
│       └── Artifacts:
│           ├── demand_model/               (trained XGBoost)
│           ├── feature_columns_config.json (column order + scaler)
│           ├── monotonicity_check.json     (price elasticity check)
│           ├── feature_importance.csv      (feature weights)
│           └── scaler.pkl                  (StandardScaler)

MLflow Model Registry:
└── Model: pia-demand-model
    └── Version 1 (Production stage)
        └── Points to Run #1's demand_model artifact
```

---

## ⚙️ Technology Stack Summary

| Component | Technology | Where |
|-----------|-----------|-------|
| **Data Storage** | Delta Tables (Spark) | Databricks |
| **ML Model** | XGBoost Regressor | Databricks |
| **Model Tracking** | MLflow Experiments | Databricks |
| **Model Registry** | MLflow Model Registry | Databricks |
| **Feature Engineering** | PySpark + Pandas | Databricks notebooks |
| **Pricing Engine** | Pure Python optimization | Databricks notebook |
| **Scheduler** | APScheduler (Databricks Jobs or notebook) | Databricks |
| **API** | FastAPI (in Databricks notebook or external) | Databricks notebook |
| **Dashboard** | Streamlit | Databricks notebook |
| **Backtesting** | Spark + Pandas simulation | Databricks notebook |

---

## 🔗 Reference: Your Original Project Structure

For reference, your original local project had:

```
C:\Users\pc\Desktop\data\
├── Data_load/                    ← Phase 2 migrates this
│   ├── flight.db (tables: flights, external_signals)
│   ├── scrapers/ (fuel, fx, competitor)
│   └── etl/
├── models/                        ← Phase 4 trains this on Databricks
│   ├── train_demand_model.py
│   ├── prepare_dataset.py
│   ├── demand_model.pkl           ← Upload this to Databricks
│   └── preprocessor.pkl           ← MLflow handles this now
├── pricing_engine/                ← Phase 6 ports this
│   ├── elasticity.py
│   ├── optimizer.py
│   └── guardrails.py
├── scheduler/                     ← Phase 7 ports this
│   ├── delta_check.py
│   └── run_autopilot.py
├── api/                           ← Phase 8 ports this
│   └── main.py
└── ui/                            ← Phase 9 ports this
    └── app.py
```

Everything in `models/`, `pricing_engine/`, `scheduler/`, `api/`, `ui/` becomes Databricks notebooks in Phases 3-9.

---

## ❓ FAQ / Troubleshooting

### "I'm stuck on Phase X. Where do I go for help?"
- Each phase document has a **Checkpoint** section at the end
- If that checkpoint fails, re-read the phase and look for red flags
- Common issues are documented at the bottom of each phase

### "Can I skip a phase?"
- **No.** Phases are sequential dependencies:
  - Phase 1 (cluster) must exist for Phases 2+
  - Phase 2 (data) must exist for Phase 3 (features)
  - Phase 3 (features) must exist for Phase 4 (training)
  - Etc.

### "How do I know if the migration was successful?"
- Finish Phase 10 (backtesting)
- Compare results with your local backtest
- Revenue uplift should be similar (+15-25%)
- Monotonic demand curve verified ✅

### "What happens if something breaks mid-way?"
- Databricks clusters are ephemeral — you can always delete and restart
- Delta tables are versioned — you can rollback if needed
- MLflow runs are immutable — past experiments preserved even if current run fails

---

## 📞 Next Steps

**You are here:** Reading this index

**What to do now:**
1. Read `DATABRICKS_MIGRATION_PHASE0.md` (account setup)
2. Complete Phase 0 on your end
3. I'll provide Phase 5 guide once Phase 4 is done (MLflow Registry)

**Timeline estimate:**
- Phases 0-4: ~1 hour (linear, must do in order)
- Phases 5-10: ~1 hour (can be parallelized or done sequentially)

---

## 📝 Notes for Your Professor

If your professor asks about the migration:

> **Summary:** We built a complete Databricks + MLflow pipeline that:
> - Takes the trained XGBoost model from local MVP
> - Registers it in MLflow Model Registry for versioning & governance
> - Implements the pricing engine, scheduler, API, and dashboard as Databricks notebooks
> - Uses Delta tables for data versioning and ACID guarantees
> - Automates model training retraining with MLflow experiment tracking
> - Demonstrates proper ML Ops patterns (model registry, experiment tracking, versioned datasets)

This shows you understand:
- ✅ Model governance (MLflow Registry)
- ✅ Experiment tracking & reproducibility (MLflow Experiments)
- ✅ Data versioning (Delta tables)
- ✅ Cloud-native architecture (Databricks)
- ✅ Autonomous ML pipelines (scheduler)

---

**Ready to start? Go to Phase 0:** `DATABRICKS_MIGRATION_PHASE0.md`
