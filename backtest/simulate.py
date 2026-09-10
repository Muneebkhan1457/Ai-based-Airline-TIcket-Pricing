"""
Compares static pricing (a fixed base_fare per route/class) against
AI dynamic pricing (pricing_engine's optimizer) across a sample of
simulated flights, measuring revenue uplift.

For each simulated flight:
  - STATIC strategy: charge base_fare flat, sell seats up to
    the actual demand_ratio recorded in flights table (booked_seats),
    i.e. what actually happened historically at that fixed price.
  - DYNAMIC strategy: run the AI optimizer for that flight's context,
    get the recommended_price and its predicted_demand_ratio, and
    compute expected revenue at that price.

This is a fair-ish comparison given we don't have real historical
A/B test data: STATIC revenue uses the REAL recorded demand at the
REAL recorded price (ground truth from the dataset), while DYNAMIC
revenue uses the model's predicted demand at the AI-recommended price.
Note this limitation explicitly in the output -- the dynamic side is
model-predicted, not independently ground-truthed, so uplift numbers
should be read as "what the model believes it would achieve" rather
than a proven real-world result.

Run from the project root:
    uv run python backtest/simulate.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

from pricing_engine.elasticity import _load_model
from pricing_engine.guardrails import apply_all_guardrails, get_price_bounds
from pricing_engine.optimizer import PRICE_STEP_PKR

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"

SAMPLE_SIZE = 1000
RANDOM_SEED = 42

def get_base_fare(conn, route, flight_class):
    row = conn.execute(
        "SELECT AVG(current_price) FROM flights WHERE route = ? AND flight_class = ?",
        (route, flight_class)
    ).fetchone()
    return row[0] if row and row[0] is not None else None

def get_competitor_stats(conn, route):
    rows = conn.execute(
        "SELECT value FROM external_signals WHERE route = ? "
        "AND signal_type LIKE 'competitor_price_%' ORDER BY recorded_date DESC",
        (route,)
    ).fetchall()
    values = [r[0] for r in rows]
    if not values:
        return None, None
    return min(values), sum(values) / len(values)

def get_signal(conn, signal_type):
    row = conn.execute(
        "SELECT value FROM external_signals WHERE signal_type = ? AND route IS NULL "
        "ORDER BY recorded_date DESC LIMIT 1",
        (signal_type,)
    ).fetchone()
    return row[0] if row else None

def sample_flights(conn, n):
    df = pd.read_sql_query("SELECT * FROM flights", conn)
    return df.sample(n=min(n, len(df)), random_state=RANDOM_SEED)

def get_remaining_seats(flight):
    if "remaining_seats" in flight and pd.notna(flight["remaining_seats"]):
        return int(flight["remaining_seats"])
    return max(int(flight["total_seats"]) - int(flight["booked_seats"]), 0)

def optimize_price_vectorized(context: dict, total_seats: int, remaining_seats: int):
    model, feature_columns = _load_model()
    floor, ceiling = get_price_bounds(context["base_fare"])
    remaining_seats_ratio = remaining_seats / total_seats

    candidate_prices = []
    price = floor
    while price <= ceiling:
        candidate_prices.append(apply_all_guardrails(
            candidate_price=price,
            base_fare=context["base_fare"],
            competitor_avg_price=context.get("competitor_avg_price"),
            days_to_departure=context["days_to_departure"],
            remaining_seats_ratio=remaining_seats_ratio,
        ))
        price += PRICE_STEP_PKR

    candidate_contexts = []
    for candidate_price in candidate_prices:
        candidate_context = dict(context)
        candidate_context["current_price"] = candidate_price
        if context.get("competitor_data_is_real") and context.get("competitor_avg_price"):
            candidate_context["price_vs_competitor_ratio"] = candidate_price / context["competitor_avg_price"]
        candidate_contexts.append(candidate_context)

    rows = pd.DataFrame(candidate_contexts)
    rows_encoded = pd.get_dummies(rows, columns=["route", "flight_class"])
    rows_encoded = rows_encoded.reindex(columns=feature_columns, fill_value=0)
    rows_encoded = rows_encoded.apply(pd.to_numeric, errors="coerce")
    
    bool_cols = [c for c in rows_encoded.columns if c.startswith("route_") or c.startswith("flight_class_")]
    for col in bool_cols:
        rows_encoded[col] = rows_encoded[col].astype(bool)
        
    predicted_demands = model.predict(rows_encoded).clip(0.0, 1.0)

    revenues = [
        candidate_price * min(remaining_seats, predicted_demand * total_seats)
        for candidate_price, predicted_demand in zip(candidate_prices, predicted_demands)
    ]
    best_index = max(range(len(revenues)), key=revenues.__getitem__)
    return {
        "recommended_price": round(float(candidate_prices[best_index]), 2),
        "expected_revenue": round(float(revenues[best_index]), 2),
        "predicted_demand_ratio": round(float(predicted_demands[best_index]), 4),
        "candidates_evaluated": len(candidate_prices),
    }

def run_backtest():
    conn = sqlite3.connect(DB_PATH)
    flights = sample_flights(conn, SAMPLE_SIZE)

    petrol = get_signal(conn, "petrol_price")
    diesel = get_signal(conn, "diesel_price")
    usd_pkr = get_signal(conn, "usd_to_pkr")

    results = []
    for _, flight in flights.iterrows():
        route = flight["route"]
        flight_class = flight["flight_class"]

        base_fare = get_base_fare(conn, route, flight_class)
        if base_fare is None:
            continue
        comp_min, comp_avg = get_competitor_stats(conn, route)

        # STATIC: real recorded outcome at the real recorded price.
        static_price = flight["current_price"]
        static_seats_sold = flight["booked_seats"]
        static_revenue = static_price * static_seats_sold

        # DYNAMIC: AI-recommended price and its predicted outcome.
        context = {
            "route": route,
            "flight_class": flight_class,
            "days_to_departure": int(flight["days_to_departure"]),
            "current_price": static_price,
            "base_fare": base_fare,
            "time_of_day": 12,
            "day_of_week": 2,
            "is_weekend": 0,
            "is_holiday_window": 0,
            "petrol_price": petrol,
            "diesel_price": diesel,
            "usd_to_pkr": usd_pkr,
            "competitor_min_price": comp_min,
            "competitor_avg_price": comp_avg,
            "price_vs_competitor_ratio": (static_price / comp_avg if comp_avg else None),
            "competitor_data_is_real": comp_avg is not None,
            "is_international": route == "KHI-DXB",
        }
        opt_result = optimize_price_vectorized(
            context,
            int(flight["total_seats"]),
            get_remaining_seats(flight),
        )
        dynamic_revenue = opt_result["expected_revenue"]

        results.append({
            "flight_id": flight["id"],
            "route": route,
            "flight_class": flight_class,
            "total_seats": int(flight["total_seats"]),
            "booked_seats": int(flight["booked_seats"]),
            "remaining_seats": get_remaining_seats(flight),
            "static_price": static_price,
            "static_revenue": static_revenue,
            "dynamic_price": opt_result["recommended_price"],
            "dynamic_revenue": dynamic_revenue,
        })

    conn.close()
    return pd.DataFrame(results)

def summarize(df: pd.DataFrame):
    total_static = df["static_revenue"].sum()
    total_dynamic = df["dynamic_revenue"].sum()
    uplift_pct = ((total_dynamic - total_static) / total_static) * 100 if total_static else 0

    print(f"\nSimulated flights: {len(df)}")
    print(f"Total STATIC revenue:  {total_static:,.0f} PKR")
    print(f"Total DYNAMIC revenue: {total_dynamic:,.0f} PKR")
    print(f"Revenue uplift: {uplift_pct:+.2f}%")
    if abs(uplift_pct) > 20:
        print("Sanity note: uplift is above 20%, so treat it as optimistic and inspect route/class drivers.")

    print("\nBy route:")
    by_route = df.groupby("route")[["static_revenue", "dynamic_revenue"]].sum()
    by_route["uplift_pct"] = (
        (by_route["dynamic_revenue"] - by_route["static_revenue"]) / by_route["static_revenue"]
    ) * 100
    print(by_route.round(2))

    print("\nIMPORTANT CAVEAT: static_revenue uses REAL recorded demand at the "
          "real recorded price (ground truth). dynamic_revenue uses the model's "
          "PREDICTED demand at the AI-recommended price -- it is not independently "
          "verified against real bookings. Read this uplift as 'what the model "
          "believes it would achieve,' not a proven real-world result.")
    print("ADDITIONAL CAVEAT: the STATIC side uses noisy single-flight historical "
          "outcomes, while the DYNAMIC side uses the model's smoothed/denoised "
          "expected demand. This noisy-real versus smoothed-model comparison can "
          "itself bias uplift estimates, especially when historical booked_seats "
          "has only weak price correlation.")

    return total_static, total_dynamic, uplift_pct

if __name__ == "__main__":
    df = run_backtest()
    df.to_csv(Path(__file__).resolve().parent / "backtest_results.csv", index=False)
    summarize(df)
    print("\nFull results saved to backtest/backtest_results.csv")
