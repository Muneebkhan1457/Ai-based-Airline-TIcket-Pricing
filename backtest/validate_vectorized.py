"""Validate vectorized backtest optimization against the original optimizer."""
import sqlite3
from pathlib import Path

import pandas as pd

from backtest import simulate
from pricing_engine.optimizer import optimize_price

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"
ROWS_PER_ROUTE_CLASS = 3
RANDOM_SEED = 42
PRICE_TOLERANCE_PKR = 0.01
REVENUE_TOLERANCE_PKR = 1.00

def build_context(conn, flight, petrol, diesel, usd_pkr):
    route = flight["route"]
    flight_class = flight["flight_class"]
    base_fare = simulate.get_base_fare(conn, route, flight_class)
    comp_min, comp_avg = simulate.get_competitor_stats(conn, route)
    return {
        "route": route,
        "flight_class": flight_class,
        "days_to_departure": int(flight["days_to_departure"]),
        "current_price": flight["current_price"],
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
        "price_vs_competitor_ratio": (flight["current_price"] / comp_avg if comp_avg else None),
        "competitor_data_is_real": comp_avg is not None,
        "is_international": route == "KHI-DXB",
    }

def sample_validation_flights(conn):
    flights = pd.read_sql_query("SELECT * FROM flights", conn)
    return (
        flights
        .groupby(["route", "flight_class"], group_keys=False)
        .apply(lambda group: group.sample(n=min(ROWS_PER_ROUTE_CLASS, len(group)), random_state=RANDOM_SEED))
        .reset_index(drop=True)
    )

def main():
    conn = sqlite3.connect(DB_PATH)
    flights = sample_validation_flights(conn)
    petrol = simulate.get_signal(conn, "petrol_price")
    diesel = simulate.get_signal(conn, "diesel_price")
    usd_pkr = simulate.get_signal(conn, "usd_to_pkr")

    rows = []
    for index, flight in flights.iterrows():
        context = build_context(conn, flight, petrol, diesel, usd_pkr)
        total_seats = int(flight["total_seats"])
        remaining_seats = simulate.get_remaining_seats(flight)
        original = optimize_price(context, total_seats, remaining_seats)
        vectorized = simulate.optimize_price_vectorized(context, total_seats, remaining_seats)
        rows.append({
            "idx": index + 1,
            "route": flight["route"],
            "flight_class": flight["flight_class"],
            "days": int(flight["days_to_departure"]),
            "total": total_seats,
            "remaining": remaining_seats,
            "original_price": original.recommended_price,
            "vectorized_price": vectorized["recommended_price"],
            "price_diff": abs(original.recommended_price - vectorized["recommended_price"]),
            "original_revenue": original.expected_revenue,
            "vectorized_revenue": vectorized["expected_revenue"],
            "revenue_diff": abs(original.expected_revenue - vectorized["expected_revenue"]),
        })

    conn.close()
    results = pd.DataFrame(rows)
    print(results.to_string(index=False))
    print(f"\nRows compared: {len(results)}")
    print(f"Max price diff: {results['price_diff'].max():.6f}")
    print(f"Max revenue diff: {results['revenue_diff'].max():.6f}")
    mismatches = results[
        (results["price_diff"] > PRICE_TOLERANCE_PKR)
        | (results["revenue_diff"] > REVENUE_TOLERANCE_PKR)
    ]
    print(f"Notable mismatches: {len(mismatches)}")
    if not mismatches.empty:
        print(mismatches.to_string(index=False))

if __name__ == "__main__":
    main()
