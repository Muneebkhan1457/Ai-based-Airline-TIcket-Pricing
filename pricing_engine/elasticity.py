"""
Wraps the saved demand model so the rest of the pricing engine can ask:
"if I set this price for this flight, what demand do I expect?"
"""
from pathlib import Path
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "demand_model.pkl"
FEATURE_COLUMNS_PATH = ROOT / "models" / "feature_columns.pkl"

_model = None
_feature_columns = None

def _load_model():
    global _model, _feature_columns
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"{MODEL_PATH} not found. Train and save the demand model first.")
        _model = joblib.load(MODEL_PATH)
        _feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
    return _model, _feature_columns

def predict_demand(context: dict) -> float:
    model, feature_columns = _load_model()
    row = pd.DataFrame([context])
    row_encoded = pd.get_dummies(row, columns=["route", "flight_class"])
    row_encoded = row_encoded.reindex(columns=feature_columns, fill_value=0)
    row_encoded = row_encoded.apply(pd.to_numeric, errors='coerce')
    prediction = model.predict(row_encoded)[0]
    return float(min(max(prediction, 0.0), 1.0))

def predict_demand_at_price(context: dict, candidate_price: float) -> float:
    updated_context = dict(context)
    updated_context["current_price"] = candidate_price
    if context.get("competitor_data_is_real") and context.get("competitor_avg_price"):
        updated_context["price_vs_competitor_ratio"] = candidate_price / context["competitor_avg_price"]
    return predict_demand(updated_context)
