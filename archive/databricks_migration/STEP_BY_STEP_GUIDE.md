# STEP-BY-STEP GUIDE: Fix All 4 Regressions

## ✅ STEP 1: Verify CSV (COMPLETE)

The file `external_signals_export.csv` exists in `C:\Users\pc\Desktop\data\` with **38 real rows**:
- Petrol prices (varying: 328.56 - 336.15 PKR/L)
- Diesel prices (varying: 385.86 - 393.04 PKR/L)
- FX rates (varying: 277.43 - 278.06)
- Competitor prices for KHI-LHE (~8.5K PKR) and KHI-ISB (~22K PKR)
- 15 holiday dates

**Status:** ✅ Ready to upload

---

## 📌 STEP 2-3: Upload CSV to Databricks

### What You'll Do:
1. Open Databricks workspace in your browser
2. Navigate to the Files section
3. Upload the CSV file
4. Note the path where it's uploaded

### Detailed Instructions:

**Option A: Upload to Databricks Volumes (Recommended)**

1. Open: https://adb-7405617912719706.6.azuredatabricks.net/ (your workspace)
2. Click **Data** in left sidebar
3. Click **Volumes**
4. Navigate to: `/airline_daw/pia_pricing/pia_data/`
5. Click **Upload** button
6. Select: `C:\Users\pc\Desktop\data\external_signals_export.csv`
7. Wait for upload to complete
8. **Path will be:** `/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv`

**Option B: Upload to Workspace (Alternative)**

1. Open: https://adb-7405617912719706.6.azuredatabricks.net/
2. Click **Workspace** in left sidebar
3. Go to your home folder (or personal workspace)
4. Click **Upload** 
5. Select: `C:\Users\pc\Desktop\data\external_signals_export.csv`
6. **Path will be:** `/Users/[your_email]/external_signals_export.csv`

**After upload, note the exact path — you'll need it in STEP 4**

---

## 📌 STEP 4: Replace Phase 3 Cell

### What to Do:

1. **In Databricks**, open your PIA pricing notebook
2. **Find Cell: "Phase 3"** (should have synthetic signals generation)
3. **Delete or Comment Out** the old Phase 3 code
4. **Create a new cell** and copy this code:

```python
# PHASE 3 (FIXED): Load Real External Signals
from pyspark.sql.functions import col

print("=" * 70)
print("PHASE 3 (FIXED): LOAD REAL EXTERNAL SIGNALS")
print("=" * 70)

# ⚠️ UPDATE THIS PATH based on where you uploaded the file
# If you uploaded to Volumes: use /Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv
# If you uploaded to Workspace: use /Users/[YOUR_EMAIL]/external_signals_export.csv
volume_path = "/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv"

try:
    df_signals_real = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(volume_path)
    )
    
    # Convert recorded_date to timestamp
    df_signals_real = df_signals_real.withColumn(
        "recorded_date", 
        col("recorded_date").cast("timestamp")
    )
    
    # Save to Delta table
    df_signals_real.write.format("delta").mode("overwrite").saveAsTable(
        "airline_daw.pia_pricing.external_signals"
    )
    
    print(f"✅ Real signals loaded and saved to Delta table")
    print(f"   Total rows: {df_signals_real.count()}")
    print(f"   Signal types: {df_signals_real.select('signal_type').distinct().count()} types")
    
    # Show distribution
    print("\n📊 SIGNAL DISTRIBUTION:")
    df_signals_real.groupby("signal_type", "route").count().show()
    
except Exception as e:
    print(f"❌ Error loading signals: {e}")
    print("Make sure the CSV path is correct and file is uploaded.")
```

5. **Replace the path:** Change `volume_path` to match where you uploaded the file
6. **Run this cell** — it should print "✅ Real signals loaded: 38 rows"

---

## 📌 STEP 5: Replace Phase 4 Cell

1. **Find Cell: "Phase 4"** (feature engineering with hardcoded values)
2. **Delete or Comment Out** the old Phase 4 code
3. **Create a new cell** and copy the ENTIRE code from: 
   - File: `C:\Users\pc\Desktop\data\DATABRICKS_CELL_04_FEATURES_FIXED.py`
   - **Copy all the code** (it's ~160 lines)
4. **Run this cell** — it should show:
   - "Real data: ~6000 rows (40.0%)"
   - "KHI-LHE: 8,5XX PKR"
   - "KHI-ISB: 2X,XXX PKR"

---

## 📌 STEP 6: Add/Replace Phase 5 Cell

1. **If Phase 5 exists:** Delete or comment it out
2. **Create a new cell** and copy the ENTIRE code from:
   - File: `C:\Users\pc\Desktop\data\DATABRICKS_CELL_05_RETRAIN_MODEL.py`
   - **Copy all the code** (~110 lines)
3. **Run this cell** — it should show:
   - "R² (test): 0.XXXX"
   - "RMSE (test): 0.XXXX"
   - Model registered to MLflow

---

## 📌 STEP 7: Check Phase 6

1. **Find Cell: "Phase 6"** (pricing engine/optimizer)
2. **Do NOT modify it**
3. **Make sure it defines:** `optimize_price()` function
4. **Run this cell** — should run without errors

---

## 📌 STEP 8: Replace Phase 7 Cell

1. **Find Cell: "Phase 7"** (scheduler with hardcoded constants)
2. **Delete or Comment Out** the old Phase 7 code
3. **Create a new cell** and copy the ENTIRE code from:
   - File: `C:\Users\pc\Desktop\data\DATABRICKS_CELL_07_SCHEDULER_FIXED.py`
   - **Copy all the code** (~210 lines)
4. **Run this cell** — it should show:
   - "KHI-LHE Competitor data is real: True"
   - "KHI-LHE Competitor avg price: 8,5XX PKR"
   - "KHI-ISB Competitor data is real: True"
   - "KHI-ISB Competitor avg price: 2X,XXX PKR"

---

## 📌 STEP 9: Replace Phase 10 Cell

1. **Find Cell: "Phase 10"** (backtest with synthetic formula)
2. **Delete or Comment Out** the old Phase 10 code
3. **Create a new cell** and copy the ENTIRE code from:
   - File: `C:\Users\pc\Desktop\data\DATABRICKS_CELL_10_BACKTEST_FIXED.py`
   - **Copy all the code** (~210 lines)
4. **Run this cell** — it should show:
   - "Revenue Uplift %: +X.XX%"
   - **(This should be DIFFERENT from +21.84%)**

---

## 📌 STEP 10: Run Full Notebook

1. **In Databricks**, make sure you have all cells (Phase 3-10)
2. **Click: "Clear All Outputs"** (optional but recommended)
3. **Click: "Run All"** at the top
4. **Wait** for the notebook to run completely (should take 2-5 minutes)
5. **Check** that all cells complete without red errors

---

## 📌 STEP 11-15: Collect Verification Outputs

As each phase completes, **copy these outputs**:

### From PHASE 3 Output:
Copy these lines:
```
✅ Real signals loaded and saved to Delta table
   Total rows: [NUMBER]
   Signal types: [NUMBER]
📊 SIGNAL DISTRIBUTION:
[TABLE OF SIGNAL TYPES]
```

### From PHASE 4 Output:
Copy these lines:
```
✅ Competitor data split (SHOULD BE ~40% real / ~60% NaN):
   Real data: [NUMBER] rows ([PERCENT]%)
   No real data: [NUMBER] rows ([PERCENT]%)

✅ Competitor prices by route:
   KHI-LHE: [PRICE] PKR
   KHI-ISB: [PRICE] PKR
```

### From PHASE 5 Output:
Copy these lines:
```
✅ TRAINING METRICS:
   R² (train): [VALUE]
   R² (test):  [VALUE]
   RMSE (train): [VALUE]
   RMSE (test):  [VALUE]
```

### From PHASE 7 Output:
Copy these lines:
```
VERIFICATION: KHI-LHE and KHI-ISB

KHI-LHE:
  ✅ Competitor data is real: [True/False]
  ✅ Competitor avg price: [PRICE] PKR
  ✅ Recommended price: [PRICE] PKR
  
KHI-ISB:
  ✅ Competitor data is real: [True/False]
  ✅ Competitor avg price: [PRICE] PKR
  ✅ Recommended price: [PRICE] PKR
```

### From PHASE 10 Output:
Copy these lines:
```
Revenue Uplift %: [VALUE]%

Note: Different from +21.84% because now using REAL model
```

---

## 📌 STEP 16: Verify All 4 Regressions Fixed

Check these 4 conditions:

**ISSUE 1 Fixed?**
- [ ] Phase 3 shows "Total rows: 38" (not 8)

**ISSUE 2 Fixed?**
- [ ] Phase 4 shows ~40% real competitor data (not always 0)
- [ ] Phase 4 shows KHI-LHE ~8,5XX PKR (not 15000)
- [ ] Phase 4 shows KHI-ISB ~2X,XXX PKR (not 15000)

**ISSUE 3 Fixed?**
- [ ] Phase 7 shows "Competitor data is real: True" for KHI-LHE
- [ ] Phase 7 shows "Competitor data is real: True" for KHI-ISB
- [ ] Phase 7 shows KHI-LHE price near 8,5XX * 1.15
- [ ] Phase 7 shows KHI-ISB price near 2X,XXX * 1.15

**ISSUE 4 Fixed?**
- [ ] Phase 10 shows uplift % DIFFERENT from +21.84%

---

## 📌 STEP 17: Report Final Results

Compile your verification outputs into this format:

```
✅ COMPLETE REGRESSION FIX REPORT

ISSUE 1 - External Signals Loaded:
  Real data rows: 38 ✅
  (From Phase 3 output: Total rows: 38)

ISSUE 2 - Features Computed from Real Signals:
  competitor_data_is_real split: [X]% True / [Y]% False ✅
  KHI-LHE competitor avg: [PRICE] PKR ✅
  KHI-ISB competitor avg: [PRICE] PKR ✅
  (From Phase 4 output)

ISSUE 3 - Scheduler Using Real Signals:
  KHI-LHE recommended price: [PRICE] PKR (capped by real competitor data) ✅
  KHI-ISB recommended price: [PRICE] PKR (capped by real competitor data) ✅
  (From Phase 7 output)

ISSUE 4 - Backtest Using Actual Optimizer:
  New uplift %: +[X.XX]% (different from +21.84%) ✅
  (From Phase 10 output)

Model Metrics (Retrained on Real Features):
  R² (test): [VALUE]
  RMSE (test): [VALUE]
  (From Phase 5 output)

STATUS: ✅ ALL 4 REGRESSIONS FIXED
```

---

## 🔍 Quick Reference: Expected Values

If things are working correctly, you should see approximately:

| Phase | Output | Expected Range |
|-------|--------|-----------------|
| 3 | Total rows | **38 exactly** |
| 4 | Real data % | **~40%** (KHI-LHE + KHI-ISB) |
| 4 | KHI-LHE price | **8,000 - 9,500 PKR** |
| 4 | KHI-ISB price | **20,000 - 25,000 PKR** |
| 5 | R² (test) | **0.3 - 0.7** (depends on model) |
| 5 | RMSE (test) | **0.1 - 0.3** (depends on model) |
| 7 | KHI-LHE cap | **9,000 - 11,000 PKR** |
| 7 | KHI-ISB cap | **22,000 - 29,000 PKR** |
| 10 | Uplift % | **+X.XX%** (anything except +21.84%) |

---

## ⚠️ Troubleshooting

### Phase 3 fails with "Path not found"
**Solution:** 
- Check the exact path where you uploaded the CSV
- Make sure path is: `/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv`
- Or: `/Users/[YOUR_EMAIL]/external_signals_export.csv`
- Update the `volume_path` variable in the cell

### Phase 4 still shows competitor_data_is_real = 0
**Solution:**
- Make sure Phase 3 ran successfully with 38 rows
- Check that signals_pdf has rows with "competitor_price_1", etc.
- Verify signal_type column values match exactly

### Phase 7 KHI-LHE still shows 15000 PKR
**Solution:**
- Restart Databricks kernel and clear outputs
- Make sure Phase 4 ran before Phase 7
- Check that get_competitor_stats() function finds real rows

### Phase 10 fails on optimize_price()
**Solution:**
- Make sure Phase 6 ran and defined the optimize_price() function
- The function must be in scope when Phase 10 runs

---

## ✅ Success!

When all phases complete and outputs match expectations:

🎉 **ALL 4 REGRESSIONS ARE FIXED!**

---

**Next: Go to Databricks and start uploading the CSV (STEP 2-3)**
