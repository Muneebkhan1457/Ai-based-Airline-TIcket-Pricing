# ✅ Execution Checklist & Timeline

Use this checklist to track your progress through the migration. Mark boxes as you complete each phase.

---

## 📅 Timeline Estimate

| Phase | Task | Time | Start | End | Status |
|-------|------|------|-------|-----|--------|
| 0 | Account setup + CLI | 15 min | -- | -- | ⬜ |
| 1 | Cluster creation | 10 min | -- | -- | ⬜ |
| 2 | Data migration | 10 min | -- | -- | ⬜ |
| 3 | Feature engineering | 20 min | -- | -- | ⬜ |
| 4 | Model training | 15 min | -- | -- | ⬜ |
| 5 | Model registry | 5 min | -- | -- | ⬜ |
| **SUBTOTAL (Phases 0-5)** | **75 min (~1.5 hours)** | | | | |
| 6 | Pricing engine | 20 min | -- | -- | ⬜ |
| 7 | Scheduler | 20 min | -- | -- | ⬜ |
| 8 | API endpoints | 20 min | -- | -- | ⬜ |
| 9 | Dashboard | 20 min | -- | -- | ⬜ |
| 10 | Backtesting | 15 min | -- | -- | ⬜ |
| **TOTAL (All Phases)** | **~2 hours** | | | | |

---

## 🟢 PHASE 0: Account & CLI Setup

**Document:** `DATABRICKS_MIGRATION_PHASE0.md`

**Checklist:**

- [ ] **Step 1:** Create Databricks account
  - [ ] Go to https://community.cloud.databricks.com/login.html
  - [ ] Sign up with email
  - [ ] Verify email
  - [ ] Log in successfully
  - Time taken: ____ min

- [ ] **Step 2:** Verify Community Edition features
  - [ ] Compute section visible
  - [ ] Workspace section visible
  - [ ] Data section visible
  - [ ] ML → Experiments visible
  - [ ] ML → Models visible
  - Time taken: ____ min

- [ ] **Step 3:** Install & Configure Databricks CLI
  - [ ] Run: `pip install databricks-cli`
  - [ ] Generate personal access token (User Settings → Access tokens)
  - [ ] Run: `databricks configure --token`
  - [ ] Enter hostname: ____________________
  - [ ] Enter token: ____________________
  - [ ] Verify: `databricks workspace list /` returns folders
  - Time taken: ____ min

- [ ] **Step 4:** Create project folder
  - [ ] Folder created: `/Users/<email>/pia-pricing-migration`
  - [ ] Folder is accessible in Workspace UI
  - Time taken: ____ min

**Phase 0 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 🟢 PHASE 1: Cluster Setup

**Document:** `DATABRICKS_MIGRATION_PHASE1.md`

**Checklist:**

- [ ] **Step 1:** Create cluster
  - [ ] Cluster name: `pia-pricing-cluster`
  - [ ] Runtime selected: ML Runtime (latest)
  - [ ] Workers: 0 (single-node)
  - [ ] Autotermination: 30 minutes
  - [ ] Cluster created & starting
  - Time taken: ____ min

- [ ] **Step 2:** Verify packages
  - [ ] Create notebook: `00_verify_packages`
  - [ ] Run import test cell
  - [ ] ✅ XGBoost imported
  - [ ] ✅ Scikit-learn imported
  - [ ] ✅ Pandas imported
  - [ ] ✅ MLflow imported
  - [ ] ✅ Joblib imported
  - Time taken: ____ min

- [ ] **Step 3:** Install additional packages (if needed)
  - [ ] Additional packages needed: __________________
  - [ ] Installed successfully (if any)
  - Time taken: ____ min

- [ ] **Step 4:** Configure MLflow
  - [ ] Create test cell with MLflow config
  - [ ] Run cell successfully
  - [ ] Experiment path verified
  - [ ] Experiment visible in ML → Experiments
  - Time taken: ____ min

**Phase 1 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 🟢 PHASE 2: Data Migration

**Document:** `DATABRICKS_MIGRATION_PHASE2.md`

**Checklist:**

- [ ] **Step 1:** Export SQLite tables to CSV (Local)
  - [ ] Run export script locally
  - [ ] ✅ `flights_export.csv` created (15,000 rows)
  - [ ] ✅ `external_signals_export.csv` created (24 rows)
  - [ ] Files in: `C:\Users\pc\Desktop\data\`
  - Time taken: ____ min

- [ ] **Step 2:** Upload CSVs to Databricks
  - [ ] Upload `flights_export.csv`
    - [ ] Table name: `flights_raw`
    - [ ] Upload complete
  - [ ] Upload `external_signals_export.csv`
    - [ ] Table name: `external_signals_raw`
    - [ ] Upload complete
  - Time taken: ____ min

- [ ] **Step 3:** Create Delta tables
  - [ ] Create notebook: `01_setup_delta_tables`
  - [ ] Cell 1 runs successfully
  - [ ] ✅ `pia_pricing.flights` Delta table created (15,000 rows)
  - [ ] ✅ `pia_pricing.external_signals` Delta table created (24 rows)
  - Time taken: ____ min

- [ ] **Step 4:** Verify data integrity
  - [ ] Create notebook: `01b_verify_data_sql` (SQL language)
  - [ ] Run SQL queries successfully
  - [ ] Row counts match local database ✅
  - [ ] Schema columns correct ✅
  - [ ] Sample rows display properly ✅
  - Time taken: ____ min

**Phase 2 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 🟢 PHASE 3: Feature Engineering

**Document:** `DATABRICKS_MIGRATION_PHASE3.md`

**Checklist:**

- [ ] **Step 1:** Create notebook
  - [ ] Notebook name: `02_prepare_dataset`
  - [ ] Language: Python
  - [ ] Cluster: `pia-pricing-cluster`
  - Time taken: ____ min

- [ ] **Cell 1 (Import & Load):** Run successfully
  - [ ] Libraries imported ✅
  - [ ] Data loaded: 15,000 flights ✅
  - [ ] Data loaded: 24 signals ✅
  - Time taken: ____ min

- [ ] **Cell 2 (Date Parsing):** Run successfully
  - [ ] Dates parsed ✅
  - [ ] Latest signals extracted ✅
  - Time taken: ____ min

- [ ] **Cell 3 (Internal Features):** Run successfully
  - [ ] Days to departure computed ✅
  - [ ] Day of week & weekend flag ✅
  - [ ] Departure time period ✅
  - [ ] Demand ratio computed ✅
  - [ ] Remaining capacity calculated ✅
  - Time taken: ____ min

- [ ] **Cell 4 (External Features):** Run successfully
  - [ ] Fuel price added ✅
  - [ ] FX rate added ✅
  - [ ] Competitor prices aggregated ✅
  - [ ] Price vs competitor ratio ✅
  - Time taken: ____ min

- [ ] **Cell 5 (Holiday Window):** Run successfully
  - [ ] Holiday dates parsed ✅
  - [ ] Holiday window feature created ✅
  - [ ] ~13% of flights in holiday window ✅
  - Time taken: ____ min

- [ ] **Cell 6 (One-Hot Encoding):** Run successfully
  - [ ] Categorical encoding applied ✅
  - [ ] Final feature count: ~50+ columns ✅
  - Time taken: ____ min

- [ ] **Cell 7 (Save Delta Table):** Run successfully
  - [ ] `pia_pricing.training_dataset` created ✅
  - [ ] Rows: 15,000 ✅
  - [ ] Columns: ~50+ ✅
  - Time taken: ____ min

- [ ] **Cell 8 (Verification):** Run successfully
  - [ ] Price-demand correlation: -0.19 to -0.41 ✅
  - [ ] Feature correlations match expectations ✅
  - Time taken: ____ min

**Phase 3 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 🟢 PHASE 4: Model Training with MLflow

**Document:** `DATABRICKS_MIGRATION_PHASE4.md`

**Checklist:**

- [ ] **Step 1:** Create notebook
  - [ ] Notebook name: `03_train_demand_model`
  - [ ] Language: Python
  - [ ] Cluster: `pia-pricing-cluster`
  - Time taken: ____ min

- [ ] **Cell 1 (Import & Load):** Run successfully
  - [ ] Libraries imported ✅
  - [ ] Training data loaded: 15,000 rows ✅
  - Time taken: ____ min

- [ ] **Cell 2 (Features & Target):** Run successfully
  - [ ] Features shape correct ✅
  - [ ] Target shape correct ✅
  - [ ] No missing values ✅
  - Time taken: ____ min

- [ ] **Cell 3 (Train-Test Split):** Run successfully
  - [ ] Training set: ~12,000 samples ✅
  - [ ] Test set: ~3,000 samples ✅
  - Time taken: ____ min

- [ ] **Cell 4 (Feature Scaling):** Run successfully
  - [ ] StandardScaler applied ✅
  - [ ] Training features scaled ✅
  - [ ] Test features scaled ✅
  - Time taken: ____ min

- [ ] **Cell 5 (MLflow Setup):** Run successfully
  - [ ] Experiment configured: `/Shared/pia-pricing-migration/demand-model` ✅
  - Time taken: ____ min

- [ ] **Cell 6 (Model Training):** Run successfully
  - [ ] XGBoost trained ✅
  - [ ] Train RMSE: ____ (expect ~0.15-0.25)
  - [ ] Test RMSE: ____ (expect ~0.20-0.30)
  - [ ] Train R²: ____ (expect ~0.25-0.5)
  - [ ] Test R²: ____ (expect ~0.20-0.45)
  - [ ] Metrics logged to MLflow ✅
  - Time taken: ____ min

- [ ] **Cell 7 (Monotonicity Check):** Run successfully
  - [ ] 🟢 **MONOTONICITY CHECK PASSED** ✅
  - [ ] Demand strictly decreases with price ✅
  - [ ] Monotonicity artifact logged ✅
  - Time taken: ____ min

- [ ] **Cell 8 (Feature Importance):** Run successfully
  - [ ] Feature importance computed ✅
  - [ ] Top features identified ✅
  - [ ] Importance artifact logged ✅
  - [ ] Column names logged ✅
  - Time taken: ____ min

- [ ] **Cell 9 (Model Logging):** Run successfully
  - [ ] Model logged to MLflow ✅
  - [ ] Model registered: `pia-demand-model` ✅
  - [ ] Scaler logged as artifact ✅
  - [ ] Run ID generated: ____________________
  - Time taken: ____ min

**Phase 4 Verification:**
- [ ] Go to **ML → Experiments** in Databricks UI
- [ ] Find `/Shared/pia-pricing-migration/demand-model`
- [ ] Click latest run
- [ ] **Params tab:** Hyperparameters visible ✅
- [ ] **Metrics tab:** RMSE, MAE, R² visible ✅
- [ ] **Artifacts tab:** 
  - [ ] `demand_model/` folder ✅
  - [ ] `feature_columns_config.json` ✅
  - [ ] `feature_importance.csv` ✅
  - [ ] `monotonicity_check.json` ✅
  - [ ] `scaler.pkl` ✅

**Phase 4 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 🟢 PHASE 5: MLflow Model Registry

**Document:** `DATABRICKS_MIGRATION_PHASE5.md`

**Checklist:**

- [ ] **Step 1:** Register the model
  - [ ] Go to **ML → Experiments**
  - [ ] Find latest run
  - [ ] Click `demand_model/` folder
  - [ ] Click "Register Model"
  - [ ] Enter name: `pia-demand-model`
  - [ ] Click Register
  - Time taken: ____ min

- [ ] **Step 2:** Verify registration
  - [ ] Go to **ML → Models**
  - [ ] Find `pia-demand-model` ✅
  - [ ] Version 1 visible ✅
  - [ ] All metrics visible ✅
  - [ ] All artifacts visible ✅
  - Time taken: ____ min

- [ ] **Step 3:** Promote to Production
  - [ ] Click `pia-demand-model` → Version 1
  - [ ] Change Stage: None → Staging
  - [ ] Confirm ✅
  - [ ] Change Stage: Staging → Production
  - [ ] Confirm ✅
  - [ ] Screenshot for professor ✅
  - Time taken: ____ min

- [ ] **Step 4:** Test model loading
  - [ ] Create notebook: `04_test_model_loading`
  - [ ] Language: Python
  - [ ] Run test cell
  - [ ] ✅ Model loaded successfully ✅
  - [ ] ✅ Sample prediction works: ____
  - [ ] ✅ Test PASSED message ✅
  - Time taken: ____ min

- [ ] **Step 5:** Document metadata
  - [ ] Create notebook: `04b_model_metadata`
  - [ ] Language: Python
  - [ ] Run metadata cell
  - [ ] All metadata displayed ✅
  - [ ] Feature configuration visible ✅
  - Time taken: ____ min

**Phase 5 Status:** ⬜ Not Started | 🟡 In Progress | 🟢 Complete

**Issues encountered:** _________________________________________________

**Resolution:** _________________________________________________

---

## 📊 PROGRESS SUMMARY

### Completed Phases:
- Phase 0: ⬜ ⬜ ⬜ ⬜ ⬜ (0/5 checkpoints)
- Phase 1: ⬜ ⬜ ⬜ ⬜ (0/4 checkpoints)
- Phase 2: ⬜ ⬜ ⬜ ⬜ (0/4 checkpoints)
- Phase 3: ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ (0/8 checkpoints)
- Phase 4: ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ (0/9 checkpoints)
- Phase 5: ⬜ ⬜ ⬜ ⬜ ⬜ (0/5 checkpoints)

**Overall Progress:** 0 / 39 checkpoints (0%)

---

## 🎯 Remaining Phases (Coming After Phase 5)

Once Phase 5 is complete:
- Phase 6: Pricing Engine (will be documented)
- Phase 7: Scheduler (will be documented)
- Phase 8: API Endpoints (will be documented)
- Phase 9: Dashboard (will be documented)
- Phase 10: Backtesting (will be documented)

---

## 📝 Notes Section

**Project Notes:**
```
Started: ________________
Target Completion: ________________
Professor Deadline: ________________

Key Metrics:
- Model RMSE: ________________
- Model R²: ________________
- Revenue Uplift: ________________%

Screenshots Taken:
- [ ] Phase 1 cluster running
- [ ] Phase 2 data uploaded
- [ ] Phase 4 model trained
- [ ] Phase 5 model in registry
```

**Blockers/Issues:**
1. ____________________________________________________________________
2. ____________________________________________________________________
3. ____________________________________________________________________

**Solutions Applied:**
1. ____________________________________________________________________
2. ____________________________________________________________________
3. ____________________________________________________________________

---

## ✅ Final Verification (After All Phases)

- [ ] All 10 phases complete
- [ ] All checkpoints passed
- [ ] Screenshots collected for professor
- [ ] Local backtest results match Databricks results
- [ ] Revenue uplift: ________% (matches expected +15-25%)
- [ ] Monotonicity check: ✅ PASSED
- [ ] All notebooks working end-to-end
- [ ] Project ready for presentation

---

**Print this checklist and track your progress. Good luck! 🚀**
