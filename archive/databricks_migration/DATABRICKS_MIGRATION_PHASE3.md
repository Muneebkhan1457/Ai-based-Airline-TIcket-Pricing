# Phase 3: Feature Engineering in Databricks

## Objective
Port your local `models/prepare_dataset.py` logic into a Databricks notebook that reads from Delta tables and produces a `training_dataset` table with all features ready for model training.

---

## Step 1: Create Feature Engineering Notebook

**New notebook:** `02_prepare_dataset`  
**Language:** Python  
**Cluster:** `pia-pricing-cluster`

---

## Step 2: Feature Engineering Code

### Cell 1: Import Libraries & Load Data

```python
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, DateType
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Load Delta tables
flights_df = spark.sql("SELECT * FROM pia_pricing.flights")
signals_df = spark.sql("SELECT * FROM pia_pricing.external_signals")

print(f"✅ Loaded flights: {flights_df.count()} rows")
print(f"✅ Loaded signals: {signals_df.count()} rows")

# Convert to pandas for feature engineering (easier for complex logic)
flights_pd = flights_df.toPandas()
signals_pd = signals_df.toPandas()

print(f"\n=== Flights Schema ===")
print(flights_pd.dtypes)
print(f"\n=== Signals Schema ===")
print(signals_pd.dtypes)
```

Run this to confirm data loads correctly.

---

### Cell 2: Parse Dates & Prepare Signals

```python
# Convert date strings to datetime if needed
if flights_pd['departure_date'].dtype == 'object':
    flights_pd['departure_date'] = pd.to_datetime(flights_pd['departure_date'])
if signals_pd['recorded_date'].dtype == 'object':
    signals_pd['recorded_date'] = pd.to_datetime(signals_pd['recorded_date'])

print("✅ Dates parsed")

# Get latest signals for each signal type
latest_signals = {}
for signal_type in signals_pd['signal_type'].unique():
    signal_data = signals_pd[signals_pd['signal_type'] == signal_type]
    latest_row = signal_data.iloc[-1]  # Most recent
    latest_signals[signal_type] = {
        'value': latest_row['value'],
        'date': latest_row['recorded_date']
    }

print("\n=== Latest Market Signals ===")
for sig_type, sig_val in latest_signals.items():
    print(f"{sig_type}: {sig_val['value']} (as of {sig_val['date'].date()})")
```

---

### Cell 3: Feature Engineering

```python
# Create a copy for feature engineering
df_train = flights_pd.copy()

# === INTERNAL FEATURES ===

# 1. Days to departure (already in data, but verify)
df_train['days_to_departure'] = (df_train['departure_date'] - datetime.now()).dt.days
df_train['days_to_departure'] = df_train['days_to_departure'].clip(lower=0)

# 2. Day of week & is_weekend
df_train['day_of_week'] = df_train['departure_date'].dt.day_name()
df_train['is_weekend'] = df_train['day_of_week'].isin(['Saturday', 'Sunday']).astype(int)

# 3. Departure time of day (parse from departure_time if available, else random)
def get_time_period(time_str):
    if pd.isna(time_str) or time_str == '':
        return 'Unknown'
    try:
        hour = int(time_str.split(':')[0])
        if 6 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 21:
            return 'Evening'
        else:
            return 'Night'
    except:
        return 'Unknown'

df_train['departure_time_period'] = df_train['departure_time'].apply(get_time_period)

# 4. Demand ratio (target variable)
df_train['demand_ratio'] = df_train['booked_seats'] / df_train['total_seats']

# 5. Remaining capacity
df_train['remaining_seats'] = df_train['total_seats'] - df_train['booked_seats']
df_train['remaining_capacity_ratio'] = df_train['remaining_seats'] / df_train['total_seats']

print("✅ Internal features engineered")
print(df_train[['days_to_departure', 'is_weekend', 'departure_time_period', 'demand_ratio', 'remaining_capacity_ratio']].head())
```

---

### Cell 4: External Market Signals

```python
# === EXTERNAL FEATURES ===

# 1. Fuel Price
fuel_price = latest_signals.get('fuel_price', {}).get('value', 330)  # default fallback
df_train['fuel_price'] = fuel_price

# 2. USD/PKR Exchange Rate
fx_rate = latest_signals.get('fx_rate', {}).get('value', 277)  # default fallback
df_train['usd_pkr_rate'] = fx_rate

# 3. Competitor prices by route
# Assume signals table has competitor_min_price and competitor_avg_price per route/date
# For now, assign random per-route (in real scenario, aggregate from signals table)

def get_competitor_price(route, price_type='min'):
    """Get competitor price for route from latest signals"""
    route_signals = signals_pd[
        (signals_pd['route'] == route) & 
        (signals_pd['signal_type'].str.contains('competitor', case=False, na=False))
    ]
    if len(route_signals) > 0:
        # Get most recent competitor signal
        latest = route_signals.iloc[-1]
        try:
            return float(latest['value'])
        except:
            return np.nan
    return np.nan

# Get unique routes
routes = df_train['route'].unique()
competitor_prices = {}
for route in routes:
    # Aggregate competitor prices for this route
    route_signals = signals_pd[signals_pd['route'] == route]
    if len(route_signals) > 0:
        competitor_prices[route] = {
            'min': float(route_signals['value'].min()),
            'avg': float(route_signals['value'].mean())
        }
    else:
        competitor_prices[route] = {'min': 15000, 'avg': 18000}  # fallback defaults

df_train['competitor_min_price'] = df_train['route'].map(lambda r: competitor_prices.get(r, {}).get('min', 15000))
df_train['competitor_avg_price'] = df_train['route'].map(lambda r: competitor_prices.get(r, {}).get('avg', 18000))

# 4. Price vs Competitor Ratio
df_train['price_vs_competitor_ratio'] = df_train['base_fare'] / df_train['competitor_avg_price']

print("✅ External market signal features engineered")
print(df_train[['fuel_price', 'usd_pkr_rate', 'competitor_min_price', 'competitor_avg_price', 'price_vs_competitor_ratio']].head())
```

---

### Cell 5: Holiday Window Feature

```python
# === HOLIDAY WINDOW FEATURE ===

# Pakistan 2026 holidays (from your scraped data)
pakistan_holidays_2026 = [
    '2026-02-05',  # Kashmir Day
    '2026-03-23',  # Pakistan Day
    '2026-05-01',  # Labour Day
    '2026-08-14',  # Independence Day
    '2026-09-30',  # Iqbal Day
    '2026-11-09',  # Iqbal Day (secondary)
    '2026-12-25',  # Quaid-e-Azam Day
    # Add Islamic holidays (approximate, varies by lunar calendar)
    '2026-04-11',  # Eid ul-Fitr (approx)
    '2026-07-07',  # Arafat Day (approx)
    '2026-07-08',  # Eid ul-Adha (approx)
    '2026-07-29',  # Islamic New Year (approx)
    '2026-09-16',  # Mawlid (approx)
]

holiday_dates = pd.to_datetime(pakistan_holidays_2026)

def is_holiday_window(departure_date, holidays, window_days=3):
    """Check if flight departs within window_days of a holiday"""
    for holiday in holidays:
        days_diff = abs((departure_date - holiday).days)
        if days_diff <= window_days:
            return 1
    return 0

df_train['is_holiday_window'] = df_train['departure_date'].apply(
    lambda d: is_holiday_window(d, holiday_dates, window_days=3)
)

print(f"✅ Holiday window feature created")
print(f"   Flights in holiday window: {df_train['is_holiday_window'].sum()} / {len(df_train)}")
print(df_train[['departure_date', 'is_holiday_window']].head(10))
```

---

### Cell 6: One-Hot Encoding & Final Dataset

```python
# === CATEGORICAL ENCODING ===

# One-hot encode categorical columns
df_train_encoded = pd.get_dummies(
    df_train,
    columns=['route', 'cabin_class', 'departure_time_period', 'day_of_week'],
    drop_first=False,
    dtype=int
)

print(f"✅ One-hot encoding complete")
print(f"   Original features: {len(df_train.columns)}")
print(f"   After encoding: {len(df_train_encoded.columns)}")

# === SELECT FINAL FEATURE SET ===

# Columns to drop (IDs, dates, leakage, originals of encoded columns)
drop_cols = [
    'flight_id', 'booking_date', 'departure_date', 'departure_time',
    'total_seats', 'booked_seats', 'base_fare',
    'route', 'cabin_class', 'departure_time_period', 'day_of_week'
]

df_training_final = df_train_encoded.drop(columns=drop_cols, errors='ignore')

# Ensure demand_ratio is the target
if 'demand_ratio' not in df_training_final.columns:
    df_training_final['demand_ratio'] = df_train['demand_ratio'].values

print(f"\n✅ Final training dataset prepared")
print(f"   Shape: {df_training_final.shape}")
print(f"   Columns: {list(df_training_final.columns)}")
print(f"\n=== First 5 rows ===")
print(df_training_final.head())

# Show target variable stats
print(f"\n=== Target Variable (demand_ratio) Stats ===")
print(df_training_final['demand_ratio'].describe())
```

---

### Cell 7: Save as Delta Table

```python
# Convert pandas DataFrame back to Spark DataFrame and save as Delta table
training_dataset_spark = spark.createDataFrame(df_training_final)

# Write to Delta table
training_dataset_spark.write.format("delta").mode("overwrite").saveAsTable("pia_pricing.training_dataset")

print(f"✅ Training dataset saved to Databricks: pia_pricing.training_dataset")
print(f"   Rows: {training_dataset_spark.count()}")
print(f"   Columns: {len(training_dataset_spark.columns)}")

# Verify it can be read back
verification = spark.sql("SELECT * FROM pia_pricing.training_dataset LIMIT 5")
verification.show()
```

---

## Step 3: Sanity Checks (Verification)

Create a final verification cell to match local behavior:

**Cell 8: Verification Metrics**

```python
import pyspark.sql.functions as F

training_df = spark.sql("SELECT * FROM pia_pricing.training_dataset")

# Convert to pandas for easier analysis
training_pd = training_df.toPandas()

# Price-demand correlation (should be negative, ~-0.19 to -0.41)
if 'current_price' in training_pd.columns and 'demand_ratio' in training_pd.columns:
    corr = training_pd['current_price'].corr(training_pd['demand_ratio'])
    print(f"Price-Demand Correlation: {corr:.4f} (expect ~-0.2 to -0.4)")

# Demand ratio distribution
print(f"\n=== Demand Ratio Distribution ===")
print(training_pd['demand_ratio'].describe())

# Check feature correlations with target
print(f"\n=== Top Feature-Target Correlations ===")
correlations = training_pd.corr()['demand_ratio'].sort_values(ascending=False)
print(correlations.head(10))

print("\n✅ Feature engineering complete & verified!")
```

---

## Next: Go to Phase 4 (Model Training with MLflow)

**Checkpoint:**
- [ ] Feature engineering notebook `02_prepare_dataset` created
- [ ] All internal features computed (days_to_departure, is_weekend, time_period, demand_ratio, etc.)
- [ ] All external features added (fuel_price, fx_rate, competitor prices, holiday window)
- [ ] One-hot encoding applied to categorical columns
- [ ] `pia_pricing.training_dataset` Delta table created with final feature set
- [ ] Sanity checks pass (correlations, distributions match local expectations)
