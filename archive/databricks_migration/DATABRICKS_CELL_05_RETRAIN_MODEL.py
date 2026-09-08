# DATABRICKS CELL: PHASE 5 (RETRAINED) - Model Training on Corrected Features
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn

print("=" * 70)
print("PHASE 5 (RETRAINED): MODEL TRAINING ON CORRECTED FEATURES")
print("=" * 70)

# Load corrected training dataset
training_df = spark.table("airline_daw.pia_pricing.training_dataset").toPandas()

print(f"\nTraining on {len(training_df)} records with REAL features")

# Select features and target
feature_columns = [
    "days_to_departure", "total_seats", "booked_seats", "remaining_seats",
    "time_of_day", "day_of_week", "is_weekend", "is_holiday_window",
    "petrol_price", "diesel_price", "usd_to_pkr", 
    "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
    "competitor_data_is_real"
]

X = training_df[feature_columns].copy()
y = training_df["demand_ratio"]

# Handle NaN values
X = X.fillna(X.mean())

print(f"\nFeature matrix shape: {X.shape}")
print(f"Target shape: {y.shape}")

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ============================================
# Start MLflow run
# ============================================

with mlflow.start_run(run_name="pia_pricing_retrained_real_signals"):
    
    # Train model on CORRECTED features
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    print("\nTraining RandomForest model...")
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Metrics
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    print(f"\n✅ TRAINING METRICS:")
    print(f"   R² (train): {r2_train:.4f}")
    print(f"   R² (test):  {r2_test:.4f}")
    print(f"   RMSE (train): {rmse_train:.4f}")
    print(f"   RMSE (test):  {rmse_test:.4f}")
    
    # Log metrics to MLflow
    mlflow.log_metric("r2_train", r2_train)
    mlflow.log_metric("r2_test", r2_test)
    mlflow.log_metric("rmse_train", rmse_train)
    mlflow.log_metric("rmse_test", rmse_test)
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n✅ TOP 5 FEATURES:")
    for idx, row in feature_importance.head(5).iterrows():
        print(f"   {row['feature']:<30} {row['importance']:.4f}")
    
    # Log model
    mlflow.sklearn.log_model(model, "model", registered_model_name="pia_pricing_model_v2_real_signals")
    
    print(f"\n✅ Model registered to MLflow as 'pia_pricing_model_v2_real_signals'")

print("\n" + "=" * 70)
print("✅ PHASE 5 COMPLETE: Model retrained on real features")
print("=" * 70)

# Store metrics for reporting
retrain_metrics = {
    'r2_test': r2_test,
    'rmse_test': rmse_test,
    'train_records': len(training_df),
    'feature_count': len(feature_columns)
}

print(f"\n📊 REPORTED METRICS:")
print(f"   R² (test): {retrain_metrics['r2_test']:.4f}")
print(f"   RMSE (test): {retrain_metrics['rmse_test']:.4f}")
