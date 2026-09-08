# QUICK START CHECKLIST: Fix All 4 Regressions

## ✅ What You Need to Do

### STEP 1: Upload CSV to Databricks (5 minutes)

- [ ] Download: `external_signals_export.csv` from `C:\Users\pc\Desktop\data\`
- [ ] In Databricks, go to: **Workspace** → **Files** (or your home folder)
- [ ] Click **Upload** and select the CSV file
- [ ] Note the path where it's uploaded (e.g., `/Users/your_email/external_signals_export.csv`)

**OR** use Databricks Volumes directly:
- [ ] Navigate to: `/Volumes/airline_daw/pia_pricing/pia_data/`
- [ ] Click **Upload** and upload the CSV there

### STEP 2: Update Your Databricks Notebook (30 minutes)

Go to your existing Databricks notebook and:

#### 2a. REPLACE Phase 3 cell

- [ ] Delete or comment out the OLD Phase 3 (synthetic signals generation)
- [ ] Copy the ENTIRE content from: `DATABRICKS_CELL_03_LOAD_SIGNALS.py`
- [ ] Paste it as a new Phase 3 cell
- [ ] Update the CSV path to match where you uploaded it in Step 1

#### 2b. REPLACE Phase 4 cell

- [ ] Delete or comment out the OLD Phase 4 (hardcoded features)
- [ ] Copy the ENTIRE content from: `DATABRICKS_CELL_04_FEATURES_FIXED.py`
- [ ] Paste it as a new Phase 4 cell
- [ ] **Do not modify** — use as-is

#### 2c. ADD new Phase 5 cell (or REPLACE if exists)

- [ ] Copy the ENTIRE content from: `DATABRICKS_CELL_05_RETRAIN_MODEL.py`
- [ ] Paste it as Phase 5 cell
- [ ] **Do not modify** — use as-is

#### 2d. KEEP Phase 6 as-is

- [ ] Do NOT modify Phase 6 (pricing optimizer)
- [ ] It should define `optimize_price()` function
- [ ] Make sure it runs without errors

#### 2e. REPLACE Phase 7 cell

- [ ] Delete or comment out the OLD Phase 7 (hardcoded scheduler)
- [ ] Copy the ENTIRE content from: `DATABRICKS_CELL_07_SCHEDULER_FIXED.py`
- [ ] Paste it as Phase 7 cell
- [ ] **Do not modify** — use as-is

#### 2f. SKIP Phases 8-9 (if they exist)

- [ ] You can skip or keep API/Dashboard phases
- [ ] They don't affect the regression fixes

#### 2g. REPLACE Phase 10 cell

- [ ] Delete or comment out the OLD Phase 10 (synthetic backtest)
- [ ] Copy the ENTIRE content from: `DATABRICKS_CELL_10_BACKTEST_FIXED.py`
- [ ] Paste it as Phase 10 cell
- [ ] **Do not modify** — use as-is

### STEP 3: Run the Full Notebook (10 minutes)

- [ ] Go to Databricks notebook
- [ ] Click **Clear** (optional, but recommended to clear old outputs)
- [ ] Click **Run All** (or **Ctrl+Alt+Enter**)
- [ ] Wait for all cells to complete (top to bottom in order)

### STEP 4: Collect Verification Results (5 minutes)

As the notebook runs, copy these outputs and paste them into a text file:

#### From Phase 3 output:
```
Total rows: ___
Signal types: ___
```

#### From Phase 4 output:
```
Real data: ___ rows (___%)
No real data: ___ rows (___%)

KHI-LHE: ___ PKR
KHI-ISB: ___ PKR
```

#### From Phase 5 output:
```
R² (test): ___
RMSE (test): ___
```

#### From Phase 7 output:
```
KHI-LHE Competitor data is real: ___
KHI-LHE Competitor avg price: ___ PKR
KHI-LHE Recommended price: ___ PKR

KHI-ISB Competitor data is real: ___
KHI-ISB Competitor avg price: ___ PKR
KHI-ISB Recommended price: ___ PKR
```

#### From Phase 10 output:
```
Revenue Uplift %: ___% (should be DIFFERENT from +21.84%)
```

### STEP 5: Verify All 4 Issues Are Fixed ✅

Check these conditions:

- [ ] **ISSUE 1**: Phase 3 shows "Total rows: 38" (not 8)
- [ ] **ISSUE 2**: Phase 4 shows ~40% real competitor data (not always 0)
- [ ] **ISSUE 3**: Phase 7 shows KHI-LHE ~8.5K PKR and KHI-ISB ~22K PKR (not hardcoded 15K)
- [ ] **ISSUE 4**: Phase 10 shows uplift % different from +21.84%

### STEP 6: Report Results

Copy this template and fill in the values from Step 4:

```
✅ ALL 4 REGRESSIONS FIXED

ISSUE 1 - External Signals Loaded:
  Real data rows: 38 ✅
  
ISSUE 2 - Features Computed from Real Signals:
  competitor_data_is_real split: 40% True / 60% False ✅
  KHI-LHE competitor avg: [VALUE] PKR ✅
  KHI-ISB competitor avg: [VALUE] PKR ✅

ISSUE 3 - Scheduler Using Real Signals:
  KHI-LHE recommended price: [VALUE] PKR (capped by real competitor data) ✅
  KHI-ISB recommended price: [VALUE] PKR (capped by real competitor data) ✅

ISSUE 4 - Backtest Using Actual Optimizer:
  New uplift %: [VALUE]% (different from +21.84%) ✅

Model Metrics (Retrained on Real Features):
  R² (test): [VALUE]
  RMSE (test): [VALUE]
```

---

## 🚨 If Something Goes Wrong

### Problem: Phase 3 fails with "Path not found"
**Fix:** Check the CSV path matches exactly where you uploaded the file in Step 1

### Problem: Phase 4 still shows competitor_data_is_real = 0 everywhere
**Fix:** Verify Phase 3 ran successfully. Check signals_pdf has rows with "competitor_price_1", etc.

### Problem: Phase 7 KHI-LHE shows 15000 PKR (old value)
**Fix:** Restart kernel and clear outputs. Phase 4 must run before Phase 7.

### Problem: Phase 10 fails on optimize_price()
**Fix:** Make sure Phase 6 ran first and defined the function. The function must be in scope.

---

## 📁 File Reference

| File | Location | Purpose |
|------|----------|---------|
| `external_signals_export.csv` | Desktop/data | Upload to Databricks — REAL signal data |
| `DATABRICKS_CELL_03_LOAD_SIGNALS.py` | Desktop/data | Copy to Phase 3 |
| `DATABRICKS_CELL_04_FEATURES_FIXED.py` | Desktop/data | Copy to Phase 4 |
| `DATABRICKS_CELL_05_RETRAIN_MODEL.py` | Desktop/data | Copy to Phase 5 |
| `DATABRICKS_CELL_07_SCHEDULER_FIXED.py` | Desktop/data | Copy to Phase 7 |
| `DATABRICKS_CELL_10_BACKTEST_FIXED.py` | Desktop/data | Copy to Phase 10 |

---

## ⏱️ Estimated Total Time

- Step 1 (Upload CSV): 5 min
- Step 2 (Update notebook): 20 min
- Step 3 (Run notebook): 10 min
- Step 4 (Collect results): 5 min
- Step 5 (Verify): 5 min
- **Total: ~45 minutes**

---

## ✅ Success Criteria

You'll know it worked when:

1. Phase 3 prints: **"✅ Real signals loaded: 38 rows"**
2. Phase 4 prints: **"Real data: 6000 rows (40.0%)"**
3. Phase 4 prints: **"KHI-LHE: 8,XXX PKR"** and **"KHI-ISB: 2X,XXX PKR"** (NOT 15000)
4. Phase 7 prints: **"Competitor data is real: True"** for KHI-LHE and KHI-ISB
5. Phase 10 prints: **"Revenue Uplift %: +X.XX%"** (different from +21.84%)

When all 5 are true → **All 4 regressions are fixed!** 🎉
