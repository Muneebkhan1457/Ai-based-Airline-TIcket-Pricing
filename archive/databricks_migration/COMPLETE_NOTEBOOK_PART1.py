# Databricks notebook source
# ============================================================
# PIA AIRLINES DYNAMIC PRICING - COMPLETE SYSTEM
# Phases 0-5: Setup, Data, Feature Engineering, Model Training
# ============================================================

# PHASE 0: MLflow Setup
import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json

mlflow.set_experiment("/Users/khaamuneeb420@gmail.com/pia-demand-model")
print("✅ Phase 0: MLflow experiment configured")

# ============================================================
# PHASE 1: Create Schema & Volume
# ============================================================

spark.sql("CREATE SCHEMA IF NOT EXISTS airline_daw.pia_pricing")
spark.sql("CREATE VOLUME IF NOT EXISTS airline_daw.pia_pricing.pia_data")
print("✅ Phase 1: Schema and volume created")

# ============================================================
# PHASE 2: Load Flights Data
# ============================================================

volume_path = "/Volumes/airline_daw/pia_pricing/pia_data/flights.csv"

df_flights_real = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(volume_path)
)

df_flights_real.write.format("delta").mode("overwrite").saveAsTable("airline_daw.pia_pricing.flights")

print(f"✅ Phase 2: Flights table created: {df_flights_real.count()} rows")

# ============================================================
# PHASE 3: Load External Signals
# ============================================================

signals_data = [
    ("petrol_price", None, 335.18),
    ("diesel_price", None, 383.46),
    ("usd_to_pkr", None, 277.86),
] + [
    ("competitor_price", route, float(np.random.uniform(12000, 20000)))
    for route in ["KHI-LHE", "KHI-ISB", "KHI-DXB", "LHE-ISB", "KHI-PEW"]
]

signals_df = spark.createDataFrame(
    signals_data,
    ["signal_type", "route", "value"]
)

signals_df.write.format("delta").mode("overwrite").saveAsTable("airline_daw.pia_pricing.external_signals")

print(f"✅ Phase 3: Signals table created: {signals_df.count()} rows")

# ============================================================
# PHASE 4: Feature Engineering
# ============================================================

flights_df = spark.table("airline_daw.pia_pricing.flights").toPandas()
signals_df = spark.table("airline_daw.pia_pricing.external_signals").toPandas()

df = flights_df.copy()

# Target variable
df["demand_ratio"] = (df["booked_seats"] / df["total_seats"]).clip(0.0, 1.0)

# Temporal features
reference_date = pd.Timestamp("2026-07-01")
df["departure_date"] = reference_date + pd.to_timedelta(df["days_to_departure"], unit="D")
df["booking_date"] = df["departure_date"]
df["time_of_day"] = (df["id"] % 24).astype(int)
df["day_of_week"] = df["departure_date"].dt.dayofweek
df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
df["is_holiday_window"] = 0

# Base fare
df["base_fare"] = df.groupby(["route", "flight_class"])["current_price"].transform("mean")

# Macro signals with noise
df["petrol_price"] = 335.18 + np.random.uniform(-10, 10, len(df))
df["diesel_price"] = 383.46 + np.random.uniform(-10, 10, len(df))
df["usd_to_pkr"] = 277.86 + np.random.uniform(-10, 10, len(df))

# Competitor pricing
df["competitor_min_price"] = 12000.0
df["competitor_avg_price"] = 15000.0
df["price_vs_competitor_ratio"] = df["current_price"] / df["competitor_avg_price"]
df["competitor_data_is_real"] = 0

# Select final features
feature_columns = [
    "id", "route", "flight_class", "days_to_departure", "total_seats", "booked_seats", "remaining_seats",
    "current_price", "base_fare", "booking_date", "time_of_day", "day_of_week", "is_weekend", "is_holiday_window",
    "petrol_price", "diesel_price", "usd_to_pkr", "competitor_min_price", "competitor_avg_price",
    "price_vs_competitor_ratio", "competitor_data_is_real", "demand_ratio"
]

final_df = df[feature_columns]

# Save to Databricks
training_dataset_spark = spark.createDataFrame(final_df)
training_dataset_spark.write.format("delta").mode("overwrite").saveAsTable("airline_daw.pia_pricing.training_dataset")

print(f"✅ Phase 4: Training dataset created: {final_df.shape}")
print(f"\nDemand Ratio Stats:")
print(final_df["demand_ratio"].describe())

# ============================================================
# PHASE 5: Model Training with MLflow Metrics
# ============================================================

training_df = spark.sql("SELECT * FROM airline_daw.pia_pricing.training_dataset").toPandas()

target_col = "demand_ratio"
X = training_df.drop(columns=[target_col], errors="ignore")
y = training_df[target_col]

# Fill missing values
X = X.fillna(0)
y = y.fillna(y.mean())

# Convert categorical columns
X = pd.get_dummies(X, columns=["route", "flight_class"])

# Define expected columns
expected_cols = [
    "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
    "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
    "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
    "competitor_data_is_real",
    "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
    "flight_class_Business", "flight_class_Economy"
]

X = X.reindex(columns=expected_cols, fill_value=0)
X = X.apply(pd.to_numeric, errors='coerce')

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"✅ Train set: {X_train.shape[0]} rows")
print(f"✅ Test set: {X_test.shape[0]} rows\n")

# Train model with MLflow tracking
with mlflow.start_run(run_name="xgboost-complete-metrics") as run:
    
    model_params = {
        "max_depth": 5,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "random_state": 42,
    }
    
    print("🔄 Training XGBoost Regressor...")
    
    # Monotonic constraints
    constraints = tuple(-1 if col in ["current_price", "price_vs_competitor_ratio"] else 0 
                       for col in expected_cols)
    
    model = XGBRegressor(
        **model_params,
        monotone_constraints=constraints
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Evaluate
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    
    print(f"\n📊 REGRESSION METRICS:")
    print(f"   Train RMSE: {train_rmse:.6f}")
    print(f"   Test RMSE:  {test_rmse:.6f} ✅")
    print(f"   Train R²:   {train_r2:.6f}")
    print(f"   Test R²:    {test_r2:.6f} ✅")
    print(f"   Train MAE:  {train_mae:.6f}")
    print(f"   Test MAE:   {test_mae:.6f}")
    
    # Verify Monotonicity
    print(f"\n🔍 MONOTONICITY CHECK:")
    base_check = {
        'days_to_departure': 10, 'base_fare': 15000,
        'time_of_day': 12, 'day_of_week': 2, 'is_weekend': 0, 'is_holiday_window': 0,
        'petrol_price': 335, 'diesel_price': 383, 'usd_to_pkr': 277,
        'competitor_min_price': 12000, 'competitor_avg_price': 14000,
        'competitor_data_is_real': 1,
        'route_KHI-LHE': 1, 'route_KHI-DXB': 0, 'route_KHI-ISB': 0, 
        'route_KHI-PEW': 0, 'route_LHE-ISB': 0,
        'flight_class_Economy': 1, 'flight_class_Business': 0
    }
    
    prices = [10000, 15000, 20000, 25000]
    preds = []
    
    for p in prices:
        ctx = base_check.copy()
        ctx['current_price'] = p
        ctx['price_vs_competitor_ratio'] = p / ctx['competitor_avg_price']
        
        row_df = pd.DataFrame([ctx]).reindex(columns=expected_cols, fill_value=0)
        row_df = row_df.apply(pd.to_numeric, errors='coerce')
        pred = model.predict(row_df)[0]
        preds.append(pred)
        print(f"   Price: {p:,} PKR → Demand: {pred:.4f}")
    
    is_monotonic = all(preds[i] >= preds[i+1] for i in range(len(preds)-1))
    print(f"\n   Result: {'✅ PASSED' if is_monotonic else '❌ FAILED'}\n")
    
    # Log to MLflow
    mlflow.log_params(model_params)
    
    metrics = {
        "train_rmse": train_rmse,
        "test_rmse": test_rmse,
        "train_r2": train_r2,
        "test_r2": test_r2,
        "train_mae": train_mae,
        "test_mae": test_mae,
        "monotonicity_passed": 1 if is_monotonic else 0,
    }
    
    for metric_name, metric_value in metrics.items():
        mlflow.log_metric(metric_name, metric_value)
    
    # Log model with signature
    mlflow.xgboost.log_model(
        model,
        artifact_path="demand_model",
        registered_model_name="pia-demand-model",
        input_example=X_test.iloc[0:5]
    )
    
    # Log config
    mlflow.log_dict(
        {'feature_columns': expected_cols},
        'feature_columns_config.json'
    )
    
    print(f"✅ Phase 5: Model Training Complete")
    print(f"   Model: pia-demand-model v1")
    print(f"   Test RMSE: {test_rmse:.6f}")
    print(f"   Test R²: {test_r2:.6f}")
    print(f"   Monotonicity: {'✅ PASSED' if is_monotonic else '❌ FAILED'}")
    print(f"   Run ID: {run.info.run_id}")

print("\n" + "=" * 70)
print("✅ PART 1 COMPLETE: Phases 0-5")
print("=" * 70)
