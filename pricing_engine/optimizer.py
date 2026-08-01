"""
Grid-search revenue-maximization engine.
Expected Revenue(P) = P * min(remaining_seats, predicted_demand(P) * total_seats)
"""
from dataclasses import dataclass
from pricing_engine.elasticity import predict_demand_at_price
from pricing_engine.guardrails import apply_all_guardrails, get_price_bounds

PRICE_STEP_PKR = 250

@dataclass
class OptimizationResult:
    recommended_price: float
    expected_revenue: float
    predicted_demand_ratio: float
    candidates_evaluated: int

def optimize_price(context: dict, total_seats: int, remaining_seats: int) -> OptimizationResult:
    base_fare = context["base_fare"]
    floor, ceiling = get_price_bounds(base_fare)
    remaining_seats_ratio = remaining_seats / total_seats

    best_price = None
    best_revenue = -1.0
    best_demand_ratio = 0.0
    candidates_evaluated = 0

    price = floor
    while price <= ceiling:
        guarded_price = apply_all_guardrails(
            candidate_price=price, base_fare=base_fare,
            competitor_avg_price=context.get("competitor_avg_price"),
            days_to_departure=context["days_to_departure"],
            remaining_seats_ratio=remaining_seats_ratio,
        )
        predicted_demand_ratio = predict_demand_at_price(context, guarded_price)
        sellable_seats = min(remaining_seats, predicted_demand_ratio * total_seats)
        expected_revenue = guarded_price * sellable_seats
        candidates_evaluated += 1

        if expected_revenue > best_revenue:
            best_revenue = expected_revenue
            best_price = guarded_price
            best_demand_ratio = predicted_demand_ratio

        price += PRICE_STEP_PKR

    return OptimizationResult(
        recommended_price=round(best_price, 2),
        expected_revenue=round(best_revenue, 2),
        predicted_demand_ratio=round(best_demand_ratio, 4),
        candidates_evaluated=candidates_evaluated,
    )
