# Phase 2: Data Migration (SQLite → Databricks)

## Objective
Export your local `flight.db` tables (`flights` and `external_signals`) to Databricks as Delta tables, making them accessible to all downstream notebooks.

---

## Step 1: Export SQLite Tables to CSV (Local)

Run this Python script locally in your project directory to export both tables:

```python
import sqlite3
import pandas as pd
import os

# Connect to your local database
db_path = r"C:\Users\pc\Desktop\data\Data_load\flight.db"
conn = sqlite3.connect(db_path)

# Export flights table
df_flights = pd.read_sql_query("SELECT * FROM flights", conn)
df_flights.to_csv("flights_export.csv", index=False)
print(f"✅ Exported flights: {len(df_flights)} rows")

# Export external_signals table
df_signals = pd.read_sql_query("SELECT * FROM external_signals", conn)
df_signals.to_csv("external_signals_export.csv", index=False)
print(f"✅ Exported external_signals: {len(df_signals)} rows")

conn.close()

print("\n✅ Both CSVs created in current directory:")
print("  - flights_export.csv")
print("  - external_signals_export.csv")
```

**Result:** Two CSV files in your local `C:\Users\pc\Desktop\data` folder.

---

## Step 2: Upload CSVs to Databricks

### Via UI (Easiest):

1. In Databricks, go to **Data** (left sidebar) → **Create table**
2. Click **Upload a file**
3. Select `flights_export.csv`
4. Click **Create table**
   - Table name: `flights_raw`
   - Cluster: `pia-pricing-cluster`
   - Click **Create**
5. Wait for upload to complete (~1-2 seconds for your small file)

6. **Repeat for `external_signals_export.csv`:**
   - Upload
   - Table name: `external_signals_raw`
   - Create

**Result:** Both tables now exist in Databricks (`default` schema).

---

## Step 3: Create Delta Tables (Production-Ready Format)

Now convert these raw CSV-backed tables into proper Delta tables (versioned, optimized).

Create a new notebook: `01_setup_delta_tables`

**Language:** Python  
**Cluster:** `pia-pricing-cluster`

**Cell 1: Load CSVs and create Delta tables**

```python
# Read the raw CSV tables that were just uploaded
df_flights = spark.sql("SELECT * FROM flights_raw")
df_signals = spark.sql("SELECT * FROM external_signals_raw")

# Create a schema/database for our project
spark.sql("CREATE SCHEMA IF NOT EXISTS pia_pricing")

# Write flights as a Delta table
df_flights.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable("pia_pricing.flights")
print(f"✅ Delta table created: pia_pricing.flights ({df_flights.count()} rows)")

# Write signals as a Delta table
df_signals.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable("pia_pricing.external_signals")
print(f"✅ Delta table created: pia_pricing.external_signals ({df_signals.count()} rows)")
```

**Run this cell.** You should see confirmation of table creation.

---

## Step 4: Verify Data Integrity

**Cell 2: Sanity checks**

```python
# Quick validation
flights_count = spark.sql("SELECT COUNT(*) as count FROM pia_pricing.flights").collect()[0][0]
signals_count = spark.sql("SELECT COUNT(*) as count FROM pia_pricing.external_signals").collect()[0][0]

print(f"Flights table: {flights_count} rows")
print(f"External signals table: {signals_count} rows")

# Show schema
print("\n=== Flights Schema ===")
spark.sql("DESCRIBE TABLE pia_pricing.flights").show()

print("\n=== External Signals Schema ===")
spark.sql("DESCRIBE TABLE pia_pricing.external_signals").show()

# Sample data
print("\n=== Sample Flights ===")
spark.sql("SELECT * FROM pia_pricing.flights LIMIT 5").show()

print("\n=== Sample Signals ===")
spark.sql("SELECT * FROM pia_pricing.external_signals LIMIT 5").show()
```

**Expected output:**
- Row counts match your local database (15,000 flights + 24 signals)
- Schema columns are correct (route, cabin_class, booked_seats, fuel_price, etc.)
- Sample rows display properly

---

## Step 5: Query Data from SQL (Optional Verification)

You can now query this data directly from SQL notebooks. Create a quick SQL verification notebook:

**New notebook: `01b_verify_data_sql`**  
**Language:** SQL

```sql
-- Check flight data distribution
SELECT 
  route, 
  cabin_class, 
  COUNT(*) as flight_count,
  AVG(booked_seats) as avg_booked,
  MAX(base_fare) as max_fare
FROM pia_pricing.flights
GROUP BY route, cabin_class
ORDER BY flight_count DESC;

-- Check signal timestamps
SELECT 
  signal_type, 
  COUNT(*) as signal_count,
  MIN(recorded_date) as earliest,
  MAX(recorded_date) as latest
FROM pia_pricing.external_signals
GROUP BY signal_type
ORDER BY signal_count DESC;
```

Run this to see your data distribution — same numbers as before should confirm migration worked ✅

---

## Next: Go to Phase 3 (Feature Engineering)

**Checkpoint:**
- [ ] `flights_export.csv` and `external_signals_export.csv` created locally
- [ ] Both CSVs uploaded to Databricks via UI
- [ ] Delta tables `pia_pricing.flights` and `pia_pricing.external_signals` created
- [ ] Row counts verified (15,000 flights + 24 signals)
- [ ] Sample queries show correct data
