"""
Test script for Phase 4 Dynamic Pricing Optimization Engine.
"""
from pricing_engine.optimizer import optimize_price

def main():
    context = {
        "route": "KHI-LHE",
        "flight_class": "Economy",
        "days_to_departure": 10,
        "base_fare": 14000,
        "competitor_avg_price": 8569,
        "competitor_data_is_real": True,
        "competitor_min_price": 7485,
        "price_vs_competitor_ratio": 1.75,
        "is_international": False,
        "petrol_price": 335,
        "diesel_price": 383,
        "usd_to_pkr": 278,
        "time_of_day": 8,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_holiday_window": 0,
        "current_price": 14000,
    }

    result = optimize_price(context, total_seats=180, remaining_seats=90)

    print("=== Optimization Result ===")
    print(f"Recommended Price: {result.recommended_price} PKR")
    print(f"Expected Revenue: {result.expected_revenue} PKR")
    print(f"Predicted Demand Ratio: {result.predicted_demand_ratio}")
    print(f"Candidates Evaluated: {result.candidates_evaluated}")

    base_fare = context["base_fare"]
    floor = 0.7 * base_fare
    ceiling = 2.5 * base_fare
    print(f"Expected Guardrail Range: [{floor:.2f}, {ceiling:.2f}] PKR")

    assert floor <= result.recommended_price <= ceiling, f"Recommended price {result.recommended_price} outside [{floor}, {ceiling}]"
    print("SUCCESS: Recommended price falls within the guardrail bounds.")

if __name__ == "__main__":
    main()
