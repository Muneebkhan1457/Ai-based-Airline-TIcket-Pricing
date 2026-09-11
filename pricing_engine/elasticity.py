"""
Wraps the saved demand model so the rest of the pricing engine can ask:
"if I set this price for this flight, what demand do I expect?"
"""
from pathlib import Path
import os
import joblib
import pandas as pd
import mlflow
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS_PATH = ROOT / "models" / "feature_columns.pkl"

_model = None
_feature_columns = None

def _get_latest_model_version() -> int:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    client = MlflowClient()
    try:
        versions = client.search_model_versions("name='pia-demand-model'")
        if versions:
            return max(int(v.version) for v in versions)
        return 1
    except Exception:
        return 1

def _load_model():
    global _model, _feature_columns
    if _model is None:
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        version = _get_latest_model_version()
        model_uri = f"models:/pia-demand-model/{version}"
        try:
            _model = mlflow.pyfunc.load_model(model_uri)
            print(f"[elasticity] Loaded pia-demand-model v{version} from DagsHub registry")
        except Exception as registry_err:
            print(f"[elasticity] Registry load failed ({registry_err}); falling back to local pkl")
            import pickle
            pkl_path = ROOT / "models" / "demand_model.pkl"
            with open(pkl_path, "rb") as f:
                raw_model = pickle.load(f)
            # Minimal wrapper so callers get a .predict() interface
            class _LocalModelWrapper:
                def __init__(self, m): self._m = m
                def predict(self, data): return self._m.predict(data)
            _model = _LocalModelWrapper(raw_model)
            print(f"[elasticity] Loaded model from local pkl: {pkl_path}")
        _feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
    return _model, _feature_columns

def predict_demand(context: dict) -> float:
    model, feature_columns = _load_model()
    row = pd.DataFrame([context])
    row_encoded = pd.get_dummies(row, columns=["route", "flight_class"])
    row_encoded = row_encoded.reindex(columns=feature_columns, fill_value=0)
    row_encoded = row_encoded.apply(pd.to_numeric, errors='coerce')
    
    bool_cols = [c for c in row_encoded.columns if c.startswith("route_") or c.startswith("flight_class_")]
    for col in bool_cols:
        row_encoded[col] = row_encoded[col].astype(bool)
        
    prediction = model.predict(row_encoded)[0]
    return float(min(max(prediction, 0.0), 1.0))

def predict_demand_at_price(context: dict, candidate_price: float) -> float:
    updated_context = dict(context)
    updated_context["current_price"] = candidate_price
    if context.get("competitor_data_is_real") and context.get("competitor_avg_price"):
        updated_context["price_vs_competitor_ratio"] = candidate_price / context["competitor_avg_price"]
    return predict_demand(updated_context)
