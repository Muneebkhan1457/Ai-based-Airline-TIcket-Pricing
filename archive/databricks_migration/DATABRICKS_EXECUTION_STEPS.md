# DATABRICKS EXECUTION STEPS: Complete Fix & Full Re-run

## CRITICAL: Run in this exact order to achieve parity

### Step 1: First-time setup (ONE TIME ONLY)

Before running any cells, you need the external_signals.csv file in your Databricks workspace.

**Option A: Manual Upload (via Databricks UI)**
1. Download `external_signals_export.csv` from `C:\Users\pc\Desktop\data\`
2. Go to Databricks workspace → File → Upload
3. Upload to: `/Users/[YOUR_USER]/external_signals_export.csv` in your personal workspace folder
4. Then reference this path in Phase 3 cell

**Option B: Use Databricks File Upload Interface**
1. Access the Volumes section in Databricks
2. Navigate to `/Volumes/airline_daw/pia_pricing/pia_data/`
3. Upload `external_signals_export.csv` directly there

---

## Step 2: Run FIXED CELLS in this exact order

⚠️ **IMPORTANT:** Run COMPLETE notebook from top to bottom. Do NOT skip cells or run out of order. Do NOT run old cells.

### Cell Order:

```
PHASE 3 (FIXED): Load Real External Signals
  → Copy content from: DATABRICKS_CELL_03_LOAD_SIGNALS.py

PHASE 4 (FIXED): Feature Engineering with Real Signals
  → Copy content from: DATABRICKS_CELL_04_FEATURES_FIXED.py

PHASE 5 (RETRAINED): Model Training on Corrected Features
  → Copy content from: DATABRICKS_CELL_05_RETRAIN_MODEL.py

PHASE 6: (EXISTING - DO NOT MODIFY)
  → Use your existing Phase 6 optimizer cell
  → Define optimize_price() function

PHASE 7 (FIXED): Scheduler with Real Signal Queries
  → Copy content from: DATABRICKS_CELL_07_SCHEDULER_FIXED.py

PHASE 10 (FIXED): Backtest Using Actual Optimizer
  → Copy content from: DATABRICKS_CELL_10_BACKTEST_FIXED.py
```

---

## Step 3: What to expect from each phase

### Phase 3 Output (Should see ~38 rows):
```
✅ Real signals loaded and saved to Delta table
   Total rows: 38
   Signal types: 6 types
📊 SIGNAL DISTRIBUTION:
   petrol_price,GLOBAL: 4
   diesel_price,GLOBAL: 4
   usd_to_pkr,GLOBAL: 4
   competitor_price_1,KHI-LHE: 1
   competitor_price_2,KHI-LHE: 1
   competitor_price_3,KHI-LHE: 1
   competitor_price_1,KHI-ISB: 1
   competitor_price_2,KHI-ISB: 1
   competitor_price_3,KHI-ISB: 1
   holiday,GLOBAL: 15
```

### Phase 4 Output (Verify these lines):
```
✅ Competitor data split (SHOULD BE ~40% real / ~60% NaN):
   Real data: 6000 rows (40.0%)
   No real data: 9000 rows (60.0%)

✅ Competitor prices by route:
   KHI-DXB: No real competitor data (NaN)
   KHI-ISB: 22,070 PKR    ← REAL, not 15000
   KHI-LHE: 8,569 PKR     ← REAL, not 15000
   KHI-PEW: No real competitor data (NaN)
   LHE-ISB: No real competitor data (NaN)
```

### Phase 5 Output (Report these metrics):
```
✅ TRAINING METRICS:
   R² (train): 0.XXXX
   R² (test):  0.XXXX
   RMSE (train): 0.XXXX
   RMSE (test):  0.XXXX
```

### Phase 7 Output (Verify KHI-LHE and KHI-ISB):
```
VERIFICATION: KHI-LHE and KHI-ISB (should have real competitor data)

KHI-LHE:
  ✅ Competitor data is real: True
  ✅ Competitor avg price: 8,569 PKR     ← NOT 15000
  ✅ Recommended price: 9,000-9,900 PKR  ← Capped near 8569*1.15
  ✅ Price capped near competitor avg * 1.15: True

KHI-ISB:
  ✅ Competitor data is real: True
  ✅ Competitor avg price: 22,070 PKR    ← NOT 15000
  ✅ Recommended price: 25,380 PKR       ← Capped near 22070*1.15
  ✅ Price capped near competitor avg * 1.15: True
```

### Phase 10 Output (Report this):
```
💰 UPLIFT ANALYSIS (Using ACTUAL Model & Optimizer)

Revenue Uplift: +[DIFFERENT FROM 21.84%] PKR
Revenue Uplift %: +X.XX%

Note: Different from +21.84% because now using REAL model
```

---

## Step 4: Verification Checklist

After full re-run, verify these 4 items match expectations:

- [ ] **ISSUE 1 Fixed:** external_signals table shows ~38 rows (not 8)
  - Verify from Phase 3 output

- [ ] **ISSUE 2 Fixed:** competitor_data_is_real shows ~40% True / 60% False split
  - Verify from Phase 4 output

- [ ] **ISSUE 3 Fixed:** KHI-LHE and KHI-ISB show real competitor prices (~8.5K, ~22K)
  - Verify from Phase 7 output

- [ ] **ISSUE 4 Fixed:** Phase 10 uplift % is different from +21.84%
  - Verify from Phase 10 output

---

## Troubleshooting

### Problem: Phase 3 fails with "Cannot find CSV"
**Solution:** 
- Verify external_signals.csv is uploaded to Databricks workspace
- Check the path matches exactly: `/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv`
- Or upload to your personal workspace: `/Users/[YOUR_USER]/external_signals_export.csv`

### Problem: Phase 4 shows competitor_avg_price still as NaN
**Solution:**
- Check Phase 3 ran successfully with 38 rows
- Check signals_pdf has competitor_price_1/2/3 rows
- Verify signal_type column values match exactly: "competitor_price_1", "competitor_price_2", etc.

### Problem: Phase 7 KHI-LHE/ISB still show competitor_data_is_real=0
**Solution:**
- Verify Phase 3 loaded real competitor data
- Check get_competitor_stats() function finds rows with signal_type starting with "competitor_price"
- Verify route names match exactly: "KHI-LHE", "KHI-ISB" (case-sensitive)

### Problem: Phase 10 fails calling optimize_price()
**Solution:**
- Make sure Phase 6 cell ran and defined optimize_price() function
- The function must be in scope when Phase 10 runs
- If Phase 6 is in a separate notebook, copy the optimize_price function into Phase 7/10 cells

---

## Final Report Template

After all phases complete, provide this report:

```
✅ COMPLETE FIX VERIFICATION REPORT

ISSUE 1 - External Signals:
  Real data rows loaded: 38 ✅
  (From Phase 3 output)

ISSUE 2 - Feature Engineering:
  competitor_data_is_real split: X% True / Y% False ✅
  KHI-LHE competitor avg: Z,ZZZ PKR ✅
  KHI-ISB competitor avg: Z,ZZZ PKR ✅
  (From Phase 4 output)

ISSUE 3 - Scheduler:
  KHI-LHE recommended price: X,XXX PKR ✅
  KHI-ISB recommended price: X,XXX PKR ✅
  Both properly capped by real competitor data ✅
  (From Phase 7 output)

ISSUE 4 - Backtest:
  New uplift %: +X.XX% (different from +21.84%) ✅
  Using actual optimize_price() function ✅
  (From Phase 10 output)

MODEL METRICS (Retrained on Real Features):
  R² (test): 0.XXXX
  RMSE (test): 0.XXXX
  (From Phase 5 output)
```
