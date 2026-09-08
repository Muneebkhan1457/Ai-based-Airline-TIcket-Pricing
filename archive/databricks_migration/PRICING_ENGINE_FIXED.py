import pandas as pd
import numpy as np
import mlflow
import mlflow.pyfunc

# ============================================
# STEP 1: Load the MLflow Model
# ============================================

model = mlflow.pyfunc.load_model(
    "models:/airline_daw.default.pia-demand-model/1"
)

print("✅ Model loaded from MLflow Registry (Version 1)")


# ============================================
# STEP 2: ELASTICITY LAYER
# ============================================

def predict_demand(context: dict, expected_cols: list) -> float:
    """Predict demand ratio given flight context and price"""

    row = pd.DataFrame([context])
    row_encoded = pd.get_dummies(row, columns=["route", "flight_class"])
    row_encoded = row_encoded.reindex(columns=expected_cols, fill_value=0)

    # Define which columns should be which type
    int_cols = ["days_to_departure", "day_of_week"]
    long_cols = ["time_of_day", "is_weekend", "is_holiday_window", "competitor_data_is_real"]
    float_cols = ["current_price", "base_fare", "petrol_price", "diesel_price", "usd_to_pkr", 
                  "competitor_min_price", "competitor_avg_price", "price_vs_competitor_ratio"]
    bool_cols = [col for col in row_encoded.columns if col.startswith("route_") or col.startswith("flight_class_")]

    # Cast to correct types
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
    return float(min(max(prediction, 0.0), 1.0))


def predict_demand_at_price(
    context: dict,
    candidate_price: float,
    expected_cols: list
) -> float:

    updated_context = dict(context)
    updated_context["current_price"] = candidate_price

    if (
        context.get("competitor_data_is_real")
        and context.get("competitor_avg_price")
    ):
        updated_context["price_vs_competitor_ratio"] = (
            candidate_price /
            context["competitor_avg_price"]
        )

    return predict_demand(
        updated_context,
        expected_cols
    )


# ============================================
# STEP 3: GUARDRAILS
# ============================================

PRICE_FLOOR_MULTIPLIER = 0.7
PRICE_CEILING_MULTIPLIER = 2.5
COMPETITOR_CEILING_MARGIN = 0.15
COMPETITOR_CEILING_CAPACITY_EXCEPTION = 0.85
URGENCY_DAYS_THRESHOLD = 3
URGENCY_CAPACITY_THRESHOLD = 0.30
PRICE_STEP_PKR = 250


def get_price_bounds(base_fare):
    return (
        base_fare * PRICE_FLOOR_MULTIPLIER,
        base_fare * PRICE_CEILING_MULTIPLIER
    )


def apply_competitor_ceiling(
    candidate_price,
    competitor_avg_price,
    capacity_used_ratio
):

    if competitor_avg_price is None:
        return candidate_price

    if capacity_used_ratio > COMPETITOR_CEILING_CAPACITY_EXCEPTION:
        return candidate_price

    max_allowed = (
        competitor_avg_price *
        (1 + COMPETITOR_CEILING_MARGIN)
    )

    return min(candidate_price, max_allowed)


def apply_urgency_modifier(
    candidate_price,
    days_to_departure,
    remaining_seats_ratio,
    boost_factor=1.10
):

    if (
        days_to_departure < URGENCY_DAYS_THRESHOLD
        and remaining_seats_ratio > URGENCY_CAPACITY_THRESHOLD
    ):
        return candidate_price * boost_factor

    return candidate_price


def apply_all_guardrails(
    candidate_price,
    base_fare,
    competitor_avg_price,
    days_to_departure,
    remaining_seats_ratio
):

    floor, ceiling = get_price_bounds(base_fare)

    # FIXED: Use max() directly, not __builtins__.max()
    price = min(max(candidate_price, floor), ceiling)

    capacity_used_ratio = 1 - remaining_seats_ratio

    price = apply_competitor_ceiling(
        price,
        competitor_avg_price,
        capacity_used_ratio
    )

    price = apply_urgency_modifier(
        price,
        days_to_departure,
        remaining_seats_ratio
    )

    return min(max(price, floor), ceiling)


# ============================================
# STEP 4: PRICE OPTIMIZER
# ============================================

class OptimizationResult:

    def __init__(
        self,
        recommended_price,
        expected_revenue,
        predicted_demand_ratio,
        candidates_evaluated
    ):

        self.recommended_price = recommended_price
        self.expected_revenue = expected_revenue
        self.predicted_demand_ratio = predicted_demand_ratio
        self.candidates_evaluated = candidates_evaluated


def optimize_price(
    context,
    total_seats,
    remaining_seats,
    expected_cols
):

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
            price,
            base_fare,
            context.get("competitor_avg_price"),
            context["days_to_departure"],
            remaining_seats_ratio
        )

        demand = predict_demand_at_price(
            context,
            guarded_price,
            expected_cols
        )

        seats = min(remaining_seats, demand * total_seats)
        revenue = guarded_price * seats
        candidates += 1

        if revenue > best_revenue:
            best_revenue = revenue
            best_price = guarded_price
            best_demand_ratio = demand

        price += PRICE_STEP_PKR

    return OptimizationResult(
        round(best_price, 2),
        round(best_revenue, 2),
        round(best_demand_ratio, 4),
        candidates
    )


print("✅ Pricing engine loaded!")


# ============================================
# STEP 5: TEST
# ============================================

expected_cols = [
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
    "route_KHI-DXB",
    "route_KHI-ISB",
    "route_KHI-LHE",
    "route_KHI-PEW",
    "route_LHE-ISB",
    "flight_class_Business",
    "flight_class_Economy"
]

test_context = {
    "days_to_departure": 10,
    "base_fare": 15000,
    "time_of_day": 12,
    "day_of_week": 2,
    "is_weekend": 0,
    "is_holiday_window": 0,
    "petrol_price": 335,
    "diesel_price": 383,
    "usd_to_pkr": 278,
    "competitor_min_price": 12000,
    "competitor_avg_price": 14000,
    "price_vs_competitor_ratio": 1.0,
    "competitor_data_is_real": 1,
    "route": "KHI-LHE",
    "flight_class": "Economy",
    "current_price": 15000
}

result = optimize_price(
    test_context,
    180,
    90,
    expected_cols
)

print("\n=== PRICING ENGINE TEST ===")
print(f"✅ Recommended Price: {result.recommended_price} PKR")
print(f"✅ Expected Revenue: {result.expected_revenue} PKR")
print(f"✅ Predicted Demand: {result.predicted_demand_ratio:.2%}")
print(f"✅ Candidates Evaluated: {result.candidates_evaluated}")
print("\n✅✅✅ PRICING ENGINE COMPLETE ✅✅✅")
