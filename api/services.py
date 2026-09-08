import os
from functools import lru_cache
from datetime import datetime

import pandas as pd
import numpy as np
import mlflow
import mlflow.pyfunc
import databricks.sql
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

load_dotenv()

# ============================================
# DATABRICKS + MLFLOW CONNECTION
# ============================================

host = os.getenv("DATABRICKS_HOST")
token = os.getenv("DATABRICKS_TOKEN")
warehouse = os.getenv("DATABRICKS_WAREHOUSE")

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")

# Lazy connection — created on first use so pytest imports don't block
_connection = None
_workspace_client = None

def _get_connection():
    global _connection
    if _connection is None:
        # databricks-sql-connector v4+ uses access_token= directly (not auth_type="pat")
        _connection = databricks.sql.connect(
            server_hostname=host,
            http_path="/sql/1.0/warehouses/" + warehouse,
            access_token=token,
        )
    return _connection

def _get_workspace_client():
    global _workspace_client
    if _workspace_client is None:
        _workspace_client = WorkspaceClient(host=host, token=token)
    return _workspace_client

MODEL_NAME = "airline_daw.default.pia-demand-model"

EXPECTED_COLS = [
    "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
    "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
    "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
    "competitor_data_is_real",
    "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
    "flight_class_Business", "flight_class_Economy",
]

ROUTES = ["KHI-LHE", "KHI-ISB", "KHI-DXB", "LHE-ISB", "KHI-PEW"]
CLASSES = ["Economy", "Business"]

# ============================================
# MODEL LOADING (latest version)
# ============================================

@lru_cache(maxsize=1)
def _get_latest_model_version() -> int:
    versions = list(_get_workspace_client().model_versions.list(MODEL_NAME))
    version_numbers = [v.version for v in versions if str(v.status.value) == "READY"]
    return max(version_numbers) if version_numbers else 1

@lru_cache(maxsize=1)
def get_model():
    """Load the latest registered model from the MLflow registry (cached)."""
    version = _get_latest_model_version()
    model_uri = f"models:/{MODEL_NAME}/{version}"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"Loaded {MODEL_NAME} v{version}")
    return model

# ============================================
# ELASTICITY LAYER (same logic as notebook Phase 6)
# ============================================

def _build_feature_row(context: dict) -> pd.DataFrame:
    row_encoded = pd.get_dummies(
        pd.DataFrame([context]), columns=["route", "flight_class"]
    )
    row_encoded = row_encoded.reindex(columns=EXPECTED_COLS, fill_value=0)

    int_cols = ["days_to_departure", "day_of_week"]
    long_cols = ["time_of_day", "is_weekend", "is_holiday_window", "competitor_data_is_real"]
    float_cols = ["current_price", "base_fare", "petrol_price", "diesel_price",
                  "usd_to_pkr", "competitor_min_price", "competitor_avg_price",
                  "price_vs_competitor_ratio"]
    bool_cols = [c for c in row_encoded.columns
                 if c.startswith("route_") or c.startswith("flight_class_")]

    for col in int_cols:
        if col in row_encoded.columns:
            row_encoded[col] = row_encoded[col].fillna(0).astype("int32")
    for col in long_cols:
        if col in row_encoded.columns:
            row_encoded[col] = row_encoded[col].fillna(0).astype("int64")
    for col in float_cols:
        if col in row_encoded.columns:
            row_encoded[col] = row_encoded[col].fillna(0.0).astype("float64")
    for col in bool_cols:
        row_encoded[col] = row_encoded[col].astype(bool)

    return row_encoded

def predict_demand(context: dict) -> float:
    """Predict demand ratio using the MLflow model."""
    model = get_model()
    row = _build_feature_row(context)
    prediction = model.predict(row)[0]
    return float(min(max(float(prediction), 0.0), 1.0))

def predict_demand_at_price(context: dict, candidate_price: float) -> float:
    """Predict demand if price were set to candidate_price."""
    updated_context = dict(context)
    updated_context["current_price"] = candidate_price
    if context.get("competitor_data_is_real") and context.get("competitor_avg_price"):
        updated_context["price_vs_competitor_ratio"] = (
            candidate_price / context["competitor_avg_price"]
        )
    return predict_demand(updated_context)

# ============================================
# GUARDRAILS (same as pricing_engine/guardrails.py)
# ============================================

PRICE_FLOOR_MULTIPLIER = 0.7
PRICE_CEILING_MULTIPLIER = 2.5
COMPETITOR_CEILING_MARGIN = 0.15
URGENCY_DAYS_THRESHOLD = 3
URGENCY_CAPACITY_THRESHOLD = 0.30
PRICE_STEP_PKR = 250


def get_price_bounds(base_fare: float):
    return (base_fare * PRICE_FLOOR_MULTIPLIER, base_fare * PRICE_CEILING_MULTIPLIER)


def apply_competitor_ceiling(candidate_price, competitor_avg_price, capacity_used_ratio):
    if competitor_avg_price is None:
        return candidate_price
    if capacity_used_ratio > 0.85:
        return candidate_price
    max_allowed = competitor_avg_price * (1 + COMPETITOR_CEILING_MARGIN)
    return min(candidate_price, max_allowed)


def apply_urgency_modifier(candidate_price, days_to_departure, remaining_seats_ratio, boost_factor=1.10):
    if days_to_departure < URGENCY_DAYS_THRESHOLD and remaining_seats_ratio > URGENCY_CAPACITY_THRESHOLD:
        return candidate_price * boost_factor
    return candidate_price


def apply_all_guardrails(candidate_price, base_fare, competitor_avg_price,
                         days_to_departure, remaining_seats_ratio):
    floor, ceiling = get_price_bounds(base_fare)
    price = min(max(candidate_price, floor), ceiling)
    capacity_used_ratio = 1 - remaining_seats_ratio
    price = apply_competitor_ceiling(price, competitor_avg_price, capacity_used_ratio)
    price = apply_urgency_modifier(price, days_to_departure, remaining_seats_ratio)
    return min(max(price, floor), ceiling)

# ============================================
# PRICE OPTIMIZER (grid search)
# ============================================

def optimize_price(context: dict, total_seats: int, remaining_seats: int) -> dict:
    """Grid search over candidate prices, pick the one that maximizes revenue."""
    base_fare = context["base_fare"]
    floor, ceiling = get_price_bounds(base_fare)
    remaining_seats_ratio = remaining_seats / total_seats

    best_price = None
    best_revenue = -1.0
    best_demand_ratio = 0.0
    candidates = 0

    price = floor
    while price <= ceiling:
        guarded_price = apply_all_guardrails(
            price, base_fare, context.get("competitor_avg_price"),
            context["days_to_departure"], remaining_seats_ratio,
        )
        demand = predict_demand_at_price(context, guarded_price)
        seats = min(remaining_seats, demand * total_seats)
        revenue = guarded_price * seats
        candidates += 1

        if revenue > best_revenue:
            best_revenue = revenue
            best_price = guarded_price
            best_demand_ratio = demand

        price += PRICE_STEP_PKR

    return {
        "recommended_price": round(best_price, 2),
        "expected_revenue": round(best_revenue, 2),
        "predicted_demand_ratio": round(best_demand_ratio, 4),
        "candidates_evaluated": candidates,
    }

# ============================================
# DATA HELPERS (Databricks SQL)
# ============================================

def get_base_fare(route: str, flight_class: str):
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT AVG(current_price) FROM airline_daw.pia_pricing.flights
           WHERE route = ? AND flight_class = ?""",
        (route, flight_class),
    )
    result = cursor.fetchone()
    cursor.close()
    return float(result[0]) if result and result[0] else None


def get_competitor_stats(route: str):
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT value FROM airline_daw.pia_pricing.external_signals
           WHERE route = ? AND signal_type LIKE '%competitor%'""",
        (route,),
    )
    rows = cursor.fetchall()
    cursor.close()
    if not rows:
        return None, None
    values = [float(r[0]) for r in rows]
    return min(values), sum(values) / len(values)


def get_signal(signal_type: str):
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT value FROM airline_daw.pia_pricing.external_signals
           WHERE signal_type = ?
           ORDER BY recorded_date DESC LIMIT 1""",
        (signal_type,),
    )
    result = cursor.fetchone()
    cursor.close()
    return float(result[0]) if result and result[0] else None


def get_holidays():
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT recorded_date FROM airline_daw.pia_pricing.external_signals
           WHERE signal_type = 'holiday'"""
    )
    rows = cursor.fetchall()
    cursor.close()
    dates = pd.to_datetime([r[0] for r in rows])
    if getattr(dates, "tz", None) is not None:
        dates = dates.tz_localize(None)
    return dates


def _build_context(route: str, flight_class: str, days_to_departure: int,
                   total_seats: int, remaining_seats: int, current_price: float,
                   base_fare: float) -> dict:
    comp_min, comp_avg = get_competitor_stats(route)
    holidays = get_holidays()

    now = datetime.now()
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    is_holiday_window = int(any(
        abs((pd.Timestamp(now.date()) - h).days) <= 2 for h in holidays
    ))

    return {
        "route": route,
        "flight_class": flight_class,
        "days_to_departure": days_to_departure,
        "current_price": current_price,
        "base_fare": base_fare,
        "time_of_day": now.hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_holiday_window": is_holiday_window,
        "petrol_price": get_signal("petrol_price") or 335.18,
        "diesel_price": get_signal("diesel_price") or 383.46,
        "usd_to_pkr": get_signal("usd_to_pkr") or 277.86,
        "competitor_min_price": comp_min if comp_min is not None else np.nan,
        "competitor_avg_price": comp_avg if comp_avg is not None else np.nan,
        "price_vs_competitor_ratio": (
            current_price / comp_avg if comp_avg else np.nan
        ),
        "competitor_data_is_real": int(comp_avg is not None),
    }

# ============================================
# PRICE_HISTORY TABLE (idempotent create)
# ============================================

def ensure_schema():
    cursor = _get_connection().cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS airline_daw.pia_pricing.price_history (
            route STRING,
            flight_class STRING,
            recommended_price DOUBLE,
            expected_revenue DOUBLE,
            predicted_demand_ratio DOUBLE,
            trigger_reason STRING,
            recorded_at STRING
        )
    """)
    cursor.close()
    _get_connection().commit()

# ============================================
# API-LEVEL FUNCTIONS
# ============================================

def get_price_recommendation(route, flight_class, days_to_departure,
                             total_seats, remaining_seats) -> dict:
    base_fare = get_base_fare(route, flight_class)
    if base_fare is None:
        raise ValueError(f"No pricing data for route={route}, class={flight_class}")

    context = _build_context(route, flight_class, days_to_departure,
                             total_seats, remaining_seats,
                             base_fare, base_fare)
    result = optimize_price(context, total_seats, remaining_seats)

    return {
        "route": route,
        "flight_class": flight_class,
        "recommended_price": result["recommended_price"],
        "expected_revenue": result["expected_revenue"],
        "predicted_demand_ratio": result["predicted_demand_ratio"],
        "candidates_evaluated": result["candidates_evaluated"],
        "competitor_data_is_real": context["competitor_data_is_real"] == 1,
    }


def insert_price_history(rows: list) -> None:
    """Insert reprice records into the Databricks price_history table."""
    ensure_schema()
    cursor = _get_connection().cursor()
    for row in rows:
        cursor.execute(
            """INSERT INTO airline_daw.pia_pricing.price_history
               (route, flight_class, recommended_price, expected_revenue,
                predicted_demand_ratio, trigger_reason, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["route"], row["flight_class"], row["recommended_price"],
                row["expected_revenue"], row["predicted_demand_ratio"],
                row.get("trigger_reason", "delta_trigger"),
                row["recorded_at"],
            ),
        )
    cursor.close()
    _get_connection().commit()


def get_representative_flight(route: str, flight_class: str) -> dict | None:
    """Fetch one representative flight for a route+class from Databricks."""
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT days_to_departure, total_seats, remaining_seats, current_price
           FROM airline_daw.pia_pricing.flights
           WHERE route = ? AND flight_class = ?
           ORDER BY days_to_departure ASC LIMIT 1""",
        (route, flight_class),
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return None
    return {
        "days_to_departure": int(row[0]),
        "total_seats": int(row[1]),
        "remaining_seats": int(row[2]),
        "current_price": float(row[3]),
    }


def reprice_all_routes(trigger_reason: str = "delta_trigger") -> dict:
    """Run the full repricing cycle for every route+class and persist to price_history."""
    ensure_schema()
    history_rows = []
    details = []

    for route in ROUTES:
        for flight_class in CLASSES:
            flight = get_representative_flight(route, flight_class)
            if flight is None:
                continue

            base_fare = get_base_fare(route, flight_class)
            if base_fare is None:
                continue

            context = _build_context(
                route, flight_class, flight["days_to_departure"],
                flight["total_seats"], flight["remaining_seats"],
                flight["current_price"], base_fare,
            )
            result = optimize_price(context, flight["total_seats"], flight["remaining_seats"])

            record = {
                "route": route,
                "flight_class": flight_class,
                "recommended_price": result["recommended_price"],
                "expected_revenue": result["expected_revenue"],
                "predicted_demand_ratio": result["predicted_demand_ratio"],
                "trigger_reason": trigger_reason,
                "recorded_at": datetime.now().isoformat(),
            }
            history_rows.append(record)
            details.append(record)

    if history_rows:
        insert_price_history(history_rows)

    return {
        "status": "ok",
        "routes_repriced": len(details),
        "details": details,
    }


def get_demand_at_price(route, flight_class, days_to_departure, price) -> dict:
    base_fare = get_base_fare(route, flight_class)
    if base_fare is None:
        raise ValueError(f"No pricing data for route={route}, class={flight_class}")

    context = _build_context(route, flight_class, days_to_departure,
                             180, 90, price, base_fare)
    demand = predict_demand_at_price(context, price)

    return {
        "route": route,
        "flight_class": flight_class,
        "price": price,
        "predicted_demand_ratio": demand,
    }


def get_signals_history(limit: int = 20) -> list:
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT signal_type, route, value, recorded_date
           FROM airline_daw.pia_pricing.external_signals
           ORDER BY recorded_date DESC LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [
        {"signal_type": r[0], "route": r[1], "value": r[2], "recorded_date": str(r[3])}
        for r in rows
    ]


def get_latest_price_history(limit: int = 10) -> list:
    cursor = _get_connection().cursor()
    cursor.execute(
        """SELECT route, flight_class, recommended_price, expected_revenue,
                  predicted_demand_ratio, trigger_reason, recorded_at
           FROM airline_daw.pia_pricing.price_history
           ORDER BY recorded_at DESC LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [
        {
            "route": r[0], "flight_class": r[1], "price": r[2],
            "expected_revenue": r[3], "predicted_demand_ratio": r[4],
            "trigger_reason": r[5], "recorded_at": r[6],
        }
        for r in rows
    ]


def check_health() -> dict:
    try:
        get_model()
        model_loaded = True
    except Exception:
        model_loaded = False
    return {
        "status": "ok",
        "database_connected": True,
        "model_loaded": model_loaded,
    }

