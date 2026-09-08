# Databricks notebook source
# ============================================================
# PIA AIRLINES DYNAMIC PRICING - COMPLETE SYSTEM
# Phases 6-7: Pricing Engine & Scheduler
# ============================================================

import pandas as pd
import numpy as np
import mlflow
import mlflow.pyfunc
from datetime import datetime, timezone
import builtins

# Fix Databricks min/max overwrite
py_min = builtins.min
py_max = builtins.max

# ============================================================
# PHASE 6: PRICING ENGINE
# ============================================================

print("=" * 70)
print("PHASE 6: PRICING ENGINE")
print("=" * 70)

# Load model from MLflow
model = mlflow.pyfunc.load_model("models:/airline_daw.default.pia-demand-model/1")
print("✅ Model loaded from MLflow Registry")

# Expected columns
expected_cols = [
    "days_to_departure", "current_price", "base_fare", "time_of_day", "day_of_week",
    "is_weekend", "is_holiday_window", "petrol_price", "diesel_price", "usd_to_pkr",
    "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio",
    "competitor_data_is_real",
    "route_KHI-DXB", "route_KHI-ISB", "route_KHI-LHE", "route_KHI-PEW", "route_LHE-ISB",
    "flight_class_Business", "flight_class_Economy"
]

# ============================================================
# ELASTICITY LAYER: Predict Demand
# ============================================================

def predict_demand(context: dict) -> float:
    """Predict demand ratio using MLflow model"""
    row = pd.DataFrame([context])
    row_encoded = pd.get_dummies(row, columns=["route", "flight_class"])
    row_encoded = row_encoded.reindex(columns=expected_cols, fill_value=0)
    
    # Type casting per MLflow schema
    int_cols = ["days_to_departure", "day_of_week"]
    long_cols = ["time_of_day", "is_weekend", "is_holiday_window", "competitor_data_is_real"]
    float_cols = ["current_price", "base_fare", "petrol_price", "diesel_price", "usd_to_pkr",
                  "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio"]
    bool_cols = [col for col in row_encoded.columns 
                 if col.startswith("route_") or col.startswith("flight_class_")]
    
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
    
    prediction = model.predict(row_encoded)[0]
    return float(py_min(py_max(float(prediction), 0.0), 1.0))


def predict_demand_at_price(context, candidate_price):
    """Predict demand at a specific price"""
    updated_context = dict(context)
    updated_context["current_price"] = candidate_price
    
    if context.get("competitor_data_is_real") and context.get("competitor_avg_price"):
        updated_context["price_vs_competitor_ratio"] = candidate_price / context["competitor_avg_price"]
    
    return predict_demand(updated_context)


print("✅ Elasticity layer initialized")

# ============================================================
# GUARDRAILS
# ============================================================

PRICE_FLOOR_MULTIPLIER = 0.7
PRICE_CEILING_MULTIPLIER = 2.5
COMPETITOR_CEILING_MARGIN = 0.15
URGENCY_DAYS_THRESHOLD = 3
URGENCY_CAPACITY_THRESHOLD = 0.30
PRICE_STEP_PKR = 250

def get_price_bounds(base_fare):
    return (base_fare * PRICE_FLOOR_MULTIPLIER, base_fare * PRICE_CEILING_MULTIPLIER)

def apply_competitor_ceiling(candidate_price, competitor_avg_price, capacity_used_ratio):
    if competitor_avg_price is None:
        return candidate_price
    
    if capacity_used_ratio > 0.85:
        return candidate_price
    
    max_allowed = competitor_avg_price * (1 + COMPETITOR_CEILING_MARGIN)
    return py_min(candidate_price, max_allowed)

def apply_urgency_modifier(candidate_price, days_to_departure, remaining_seats_ratio, boost_factor=1.10):
    if days_to_departure < URGENCY_DAYS_THRESHOLD and remaining_seats_ratio > URGENCY_CAPACITY_THRESHOLD:
        return candidate_price * boost_factor
    return candidate_price

def apply_all_guardrails(candidate_price, base_fare, competitor_avg_price, days_to_departure, remaining_seats_ratio):
    floor, ceiling = get_price_bounds(base_fare)
    price = py_min(py_max(candidate_price, floor), ceiling)
    
    capacity_used_ratio = 1 - remaining_seats_ratio
    price = apply_competitor_ceiling(price, competitor_avg_price, capacity_used_ratio)
    price = apply_urgency_modifier(price, days_to_departure, remaining_seats_ratio)
    price = py_min(py_max(price, floor), ceiling)
    
    return price

print("✅ Guardrails initialized")

# ============================================================
# PRICE OPTIMIZER
# ============================================================

class OptimizationResult:
    def __init__(self, recommended_price, expected_revenue, predicted_demand_ratio, candidates_evaluated):
        self.recommended_price = recommended_price
        self.expected_revenue = expected_revenue
        self.predicted_demand_ratio = predicted_demand_ratio
        self.candidates_evaluated = candidates_evaluated

def optimize_price(context, total_seats, remaining_seats):
    """Grid search optimization: maximize revenue"""
    base_fare = context["base_fare"]
    floor, ceiling = get_price_bounds(base_fare)
    remaining_seats_ratio = remaining_seats / total_seats
    
    best_price = None
    best_revenue = -1
    best_demand_ratio = 0
    candidates = 0
    
    price = floor
    while price <= ceiling:
        guarded_price = apply_all_guardrails(
            price, base_fare, context.get("competitor_avg_price"),
            context["days_to_departure"], remaining_seats_ratio
        )
        
        demand = predict_demand_at_price(context, guarded_price)
        seats = py_min(remaining_seats, demand * total_seats)
        revenue = guarded_price * seats
        candidates += 1
        
        if revenue > best_revenue:
            best_revenue = revenue
            best_price = guarded_price
            best_demand_ratio = demand
        
        price += PRICE_STEP_PKR
    
    return OptimizationResult(round(best_price, 2), round(best_revenue, 2), round(best_demand_ratio, 4), candidates)

print("✅ Price optimizer initialized")

# ============================================================
# PHASE 7: SCHEDULER
# ============================================================

print("\n" + "=" * 70)
print("PHASE 7: AUTONOMOUS SCHEDULER")
print("=" * 70)

_last_known_signals = {}
price_history = []

def check_for_changes(current_signals):
    """Detects market signal changes"""
    global _last_known_signals
    
    changed_keys = []
    for key, value in current_signals.items():
        if key not in _last_known_signals or _last_known_signals[key] != value:
            changed_keys.append(key)
    
    affected_routes = {route for (route, signal_type) in changed_keys if route is not None}
    global_changed = any(route is None for (route, signal_type) in changed_keys)
    
    _last_known_signals = current_signals.copy()
    
    return {
        "changed": len(changed_keys) > 0,
        "changed_keys": changed_keys,
        "affected_routes": affected_routes,
        "global_changed": global_changed,
    }

def reprice_route(flights_df, signals_df, route, flight_class):
    """Reprice a specific route + class"""
    subset = flights_df[
        (flights_df["route"] == route) & 
        (flights_df["flight_class"] == flight_class)
    ]
    
    if len(subset) == 0:
        return
    
    flight = subset.iloc[0]
    base_fare = flights_df[
        (flights_df["route"] == route) & 
        (flights_df["flight_class"] == flight_class)
    ]["current_price"].mean()
    
    now = datetime.now()
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    
    context = {
        'route': route,
        'flight_class': flight_class,
        'days_to_departure': int(flight["days_to_departure"]),
        'current_price': float(flight["current_price"]),
        'base_fare': float(base_fare),
        'time_of_day': now.hour,
        'day_of_week': day_of_week,
        'is_weekend': is_weekend,
        'is_holiday_window': 0,
        'petrol_price': 335.18,
        'diesel_price': 383.46,
        'usd_to_pkr': 277.86,
        'competitor_min_price': 12000.0,
        'competitor_avg_price': 15000.0,
        'price_vs_competitor_ratio': float(flight["current_price"]) / 15000.0,
        'competitor_data_is_real': 0,
    }
    
    opt_result = optimize_price(context, int(flight["total_seats"]), int(flight["remaining_seats"]))
    
    price_history.append({
        "route": route,
        "flight_class": flight_class,
        "recommended_price": opt_result.recommended_price,
        "expected_revenue": opt_result.expected_revenue,
        "predicted_demand_ratio": opt_result.predicted_demand_ratio,
        "trigger_reason": "delta_trigger",
        "recorded_at": datetime.now(timezone.utc).isoformat()
    })
    
    print(f"[{route}/{flight_class}] Price: {opt_result.recommended_price} PKR | Revenue: {opt_result.expected_revenue}")

def scheduled_check(flights_df, signals_df):
    """Run periodic signal check"""
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running scheduled signal check...")
    
    current_signals = {}
    for _, row in signals_df.iterrows():
        key = (str(row["route"]), str(row["signal_type"]))
        current_signals[key] = float(row["value"]) if row["value"] is not None else 0
    
    delta = check_for_changes(current_signals)
    
    if not delta["changed"]:
        print("✅ No market changes detected. Prices remain unchanged.")
        return
    
    print(f"⚠️ Change detected: {len(delta['changed_keys'])} signals")
    
    routes_to_reprice = delta["affected_routes"]
    if delta["global_changed"]:
        routes_to_reprice = {"KHI-LHE", "KHI-ISB", "KHI-DXB", "LHE-ISB", "KHI-PEW"}
    
    print(f"Repricing {len(routes_to_reprice)} routes...")
    
    for route in routes_to_reprice:
        for flight_class in ["Economy", "Business"]:
            reprice_route(flights_df, signals_df, route, flight_class)

# Test scheduler
flights_df = spark.table("airline_daw.pia_pricing.flights").toPandas()
signals_df = spark.table("airline_daw.pia_pricing.external_signals").toPandas()

scheduled_check(flights_df, signals_df)

print(f"\n✅ Phase 7: Scheduler Complete")
print(f"   Price history records: {len(price_history)}")

# Save price history to Databricks
if len(price_history) > 0:
    history_df = spark.createDataFrame(price_history)
    history_df.write.format("delta").mode("overwrite").saveAsTable("airline_daw.pia_pricing.price_history")
    print(f"   Saved to price_history table")

print("\n" + "=" * 70)
print("✅ PART 2 COMPLETE: Phases 6-7")
print("=" * 70)
