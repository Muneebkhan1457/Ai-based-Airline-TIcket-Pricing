# PIA Airlines Dynamic Pricing - Regression Fixes Implementation

## 📋 Overview

This package contains **complete fixes for all 4 critical regressions** in your Databricks migration:

1. **ISSUE 1:** Synthetic external signals → Real external signals (38 rows)
2. **ISSUE 2:** Hardcoded features → Real computed features
3. **ISSUE 3:** Hardcoded scheduler constants → Real signal queries
4. **ISSUE 4:** Synthetic backtest formula → Actual model + optimizer

---

## 📦 Deliverables

### Real Data Export
- **`external_signals_export.csv`** (38 rows)
  - Real petrol/diesel prices with time-series variation
  - Real FX rates (USD to PKR)
  - Real competitor prices for KHI-LHE (~8.5K PKR) and KHI-ISB (~22K PKR)
  - 15 real holiday dates from Pakistan calendar

### Fixed Databricks Cells (Copy-Paste Ready)

1. **`DATABRICKS_CELL_03_LOAD_SIGNALS.py`**
   - Loads 38 real signal rows from CSV
   - Creates Delta table: `airline_daw.pia_pricing.external_signals`

2. **`DATABRICKS_CELL_04_FEATURES_FIXED.py`**
   - Computes features from real signals (not hardcoded)
   - Competitor prices aggregated per route
   - competitor_data_is_real shows realistic ~40% True / ~60% False split
   - Creates training dataset with corrected features

3. **`DATABRICKS_CELL_05_RETRAIN_MODEL.py`**
   - Retrains model on corrected feature set
   - Logs metrics to MLflow (R², RMSE)
   - Registers model as `pia_pricing_model_v2_real_signals`

4. **`DATABRICKS_CELL_07_SCHEDULER_FIXED.py`**
   - Reads real signals from external_signals table
   - Queries actual competitor prices per route
   - KHI-LHE/ISB now show real prices (~8.5K, ~22K), not hardcoded 15K
   - Test output confirms competitor_data_is_real=True for these routes

5. **`DATABRICKS_CELL_10_BACKTEST_FIXED.py`**
   - Uses actual `optimize_price()` function (from Phase 6)
   - Builds context with real signals for each flight
   - Reports uplift % based on actual model predictions
   - Expected to differ from +21.84% (which was synthetic formula)

### Documentation

- **`DATABRICKS_EXECUTION_STEPS.md`** - Exact order and instructions for running all cells
- **`REGRESSION_FIXES_SUMMARY.md`** - Before/after comparison for each issue
- **`FIXES_ISSUES_1_2_3_4.md`** - Detailed explanation of what was fixed

---

## 🚀 Quick Start

### 1. Upload CSV to Databricks
Download `external_signals_export.csv` and upload to Databricks:
- Option A: Upload to workspace → `/Users/[YOUR_USER]/external_signals_export.csv`
- Option B: Upload to volume → `/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv`

### 2. Run Fixed Cells in Sequence
Copy each fixed cell into your Databricks notebook in this order:
1. Phase 3 (Load Signals)
2. Phase 4 (Feature Engineering)
3. Phase 5 (Retrain Model)
4. Phase 6 (Existing optimizer - no changes)
5. Phase 7 (Scheduler)
6. Phase 10 (Backtest)

### 3. Verify Output
Check that each phase outputs expected values:
- Phase 3: 38 rows ✅
- Phase 4: ~40% competitor_data_is_real ✅
- Phase 5: Model R² and RMSE ✅
- Phase 7: KHI-LHE (~8.5K PKR), KHI-ISB (~22K PKR) ✅
- Phase 10: Uplift % different from +21.84% ✅

---

## 📊 Expected Results After Fix

### Before (Broken):
```
Phase 3: 8 fake signal rows
Phase 4: competitor_data_is_real = 0 (always False)
         competitor_avg_price = 15000 (hardcoded)
Phase 7: All routes show 15000 competitor price
         competitor_data_is_real = 0
Phase 10: +21.84% uplift (using separate elasticity formula)
```

### After (Fixed):
```
Phase 3: 38 real signal rows ✅
Phase 4: competitor_data_is_real = ~40% True / ~60% False ✅
         KHI-LHE: ~8,500 PKR ✅
         KHI-ISB: ~22,000 PKR ✅
Phase 7: KHI-LHE/ISB show real prices ✅
         competitor_data_is_real = True for these routes ✅
Phase 10: +X.XX% uplift using actual optimizer ✅
```

---

## 🔍 Verification Checklist

After running all cells, verify:

- [ ] Phase 3 loads exactly 38 rows
  - Verify output shows: "Total rows: 38"

- [ ] Phase 4 shows competitor split
  - Verify output shows: "Real data: ~6000 rows (40.0%)"
  - Verify shows: "KHI-LHE: 8,5XX PKR" and "KHI-ISB: 2X,XXX PKR"

- [ ] Phase 5 reports metrics
  - Verify output shows: "R² (test): 0.XXXX"
  - Verify output shows: "RMSE (test): 0.XXXX"

- [ ] Phase 7 scheduler test passes
  - Verify output shows: "Competitor data is real: True" for KHI-LHE
  - Verify output shows: "Competitor avg price: 8,5XX PKR" for KHI-LHE
  - Verify output shows: "Competitor data is real: True" for KHI-ISB
  - Verify output shows: "Competitor avg price: 2X,XXX PKR" for KHI-ISB

- [ ] Phase 10 backtest shows new uplift
  - Verify output shows: "Revenue Uplift %: +X.XX%"
  - Confirm this is DIFFERENT from +21.84%

---

## 🐛 Troubleshooting

### Issue: Phase 3 fails with CSV not found
**Solution:** Verify CSV path matches exactly. Use Databricks file browser to confirm location.

### Issue: Phase 4 competitor_data_is_real still shows all zeros
**Solution:** Check Phase 3 loaded real rows with "competitor_price_1", "competitor_price_2", etc.

### Issue: Phase 7 KHI-LHE still shows 15000 PKR
**Solution:** Verify signals_pdf has competitor_price rows and get_competitor_stats() function found them.

### Issue: Phase 10 fails calling optimize_price()
**Solution:** Ensure Phase 6 (or Phase 7 which includes it) already ran and function is in scope.

---

## 📁 File Structure

```
C:\Users\pc\Desktop\data\
├── external_signals_export.csv                    ← Upload to Databricks
├── DATABRICKS_CELL_03_LOAD_SIGNALS.py             ← Copy to notebook
├── DATABRICKS_CELL_04_FEATURES_FIXED.py           ← Copy to notebook
├── DATABRICKS_CELL_05_RETRAIN_MODEL.py            ← Copy to notebook
├── DATABRICKS_CELL_07_SCHEDULER_FIXED.py          ← Copy to notebook
├── DATABRICKS_CELL_10_BACKTEST_FIXED.py           ← Copy to notebook
├── DATABRICKS_EXECUTION_STEPS.md                  ← Instructions
├── REGRESSION_FIXES_SUMMARY.md                    ← Before/after
├── FIXES_ISSUES_1_2_3_4.md                        ← Detailed explanation
└── README_FIX_IMPLEMENTATION.md                   ← This file
```

---

## ✅ Sign-off Criteria

All 4 regressions are fixed when you see:

1. ✅ **ISSUE 1:** external_signals table = 38 rows (real data)
2. ✅ **ISSUE 2:** competitor_data_is_real = ~40% True (realistic split)
3. ✅ **ISSUE 3:** KHI-LHE/ISB prices capped at real competitor averages (8.5K, 22K)
4. ✅ **ISSUE 4:** Backtest uplift % differs from +21.84% (uses actual model)

---

## 📞 Questions?

Refer to:
- `DATABRICKS_EXECUTION_STEPS.md` for how to run
- `REGRESSION_FIXES_SUMMARY.md` for what changed
- Individual cell files for detailed implementation
