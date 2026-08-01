"""
Standalone XGBoost demand model training script.
Ensures monotonicity constraints on price features and saves demand_model.pkl and feature_columns.pkl.
"""
import pickle
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "models" / "training_dataset.csv"
MODEL_PATH = ROOT / "models" / "demand_model.pkl"
COLS_PATH = ROOT / "models" / "feature_columns.pkl"

def main():
    if not DATASET_PATH.exists():
        print(f"Error: Dataset {DATASET_PATH} not found. Run prepare_dataset.py first.")
        return

    # Load dataset
    df = pd.read_csv(DATASET_PATH)
    print(f"Loaded dataset with shape: {df.shape}")

    # Define targets and predictors
    target_col = "demand_ratio"
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in dataset.")

    y = df[target_col].clip(0.0, 1.0)
    
    # Feature columns expected by prediction pipeline
    feature_cols = [
        "days_to_departure",
        "current_price",
        "base_fare",
        "time_of_day",
        "day_of_week",
        "is_weekend",
        "is_holiday_window",
        "petrol_price",
        "diesel_price",
        "usd_to_pkr",
        "competitor_min_price",
        "competitor_avg_price",
        "price_vs_competitor_ratio",
        "competitor_data_is_real",
        "route",
        "flight_class"
    ]

    # Sub-select features and one-hot encode
    X = df[feature_cols].copy()
    X = pd.get_dummies(X, columns=["route", "flight_class"])

    # Ensure exact same list of columns as expected by the verified feature set
    expected_cols = [
        "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
        "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
        "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
        "competitor_data_is_real",
        "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
        "flight_class_Business", "flight_class_Economy"
    ]

    X = X.reindex(columns=expected_cols, fill_value=0)
    # Convert all columns to numeric type
    X = X.apply(pd.to_numeric, errors='coerce')

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Set up monotone constraints
    constraints = {}
    for col in expected_cols:
        if col in ["current_price", "price_vs_competitor_ratio"]:
            constraints[col] = -1
        else:
            constraints[col] = 0

    # Build model tuple of constraints corresponding to column order
    monotone_constraints = tuple(constraints[col] for col in expected_cols)

    # Train XGBoost regressor
    print("Training XGBoost Regressor with Monotonic Constraints...")
    model = xgb.XGBRegressor(
        max_depth=5,
        learning_rate=0.1,
        n_estimators=100,
        random_state=42,
        monotone_constraints=monotone_constraints
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"Evaluation Results:")
    print(f"  Test RMSE: {rmse:.4f}")
    print(f"  Test R2:   {r2:.4f}")

    # Verify Monotonicity Price-Check
    print("\nVerifying monotonicity check on sample data:")
    base_check = {
        'days_to_departure': 10,
        'base_fare': 15000,
        'time_of_day': 12, 'day_of_week': 2, 'is_weekend': 0, 'is_holiday_window': 0,
        'petrol_price': 280, 'diesel_price': 280, 'usd_to_pkr': 278,
        'competitor_min_price': 12000, 'competitor_avg_price': 14000,
        'competitor_data_is_real': True, 'route_KHI-LHE': 1, 'flight_class_Economy': 1
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
        print(f"  Price: {p} PKR -> Predicted Demand Ratio: {pred:.4f}")

    # Check that predictions are indeed non-increasing
    is_monotonic = all(preds[i] >= preds[i+1] for i in range(len(preds)-1))
    if not is_monotonic:
        print("WARNING: Model is not monotonic! Check constraints.")
    else:
        print("SUCCESS: Monotonicity verified.")

    # Save files
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(COLS_PATH, "wb") as f:
        pickle.dump(expected_cols, f)
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved feature columns list to {COLS_PATH}")

if __name__ == "__main__":
    main()
