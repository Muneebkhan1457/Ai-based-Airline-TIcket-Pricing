"""
Business logic layer connecting the API to the demand model and
pricing engine -- mirrors the context-building logic already used in
scheduler/run_autopilot.py's build_context_for_route (including the
real datetime-based temporal/holiday features, not hardcoded values).
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from pricing_engine.optimizer import optimize_price

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"

def get_base_fare(conn, route: str, flight_class: str):
    row = conn.execute(
        "SELECT AVG(current_price) FROM flights WHERE route = ? AND flight_class = ?",
        (route, flight_class)
    ).fetchone()
    return row[0] if row and row[0] is not None else None

def get_competitor_stats(conn, route: str):
    rows = conn.execute(
        "SELECT value FROM external_signals WHERE route = ? "
        "AND signal_type LIKE 'competitor_price_%' "
        "ORDER BY recorded_date DESC",
        (route,)
    ).fetchall()
    values = [r[0] for r in rows]
    if not values:
        return None, None
    return min(values), sum(values) / len(values)

def get_signal(conn, signal_type, route_filter=None):
    row = conn.execute(
        "SELECT value FROM external_signals WHERE signal_type = ? AND "
        "(route = ? OR route IS NULL) ORDER BY recorded_date DESC LIMIT 1",
        (signal_type, route_filter)
    ).fetchone()
    return row[0] if row else None

def get_price_recommendation(route: str, flight_class: str, days_to_departure: int,
                              total_seats: int, remaining_seats: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        base_fare = get_base_fare(conn, route, flight_class)
        if base_fare is None:
            raise ValueError(f"No pricing data found for route={route}, class={flight_class}")

        comp_min, comp_avg = get_competitor_stats(conn, route)

        now = datetime.now()
        day_of_week = now.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        holiday_dates = conn.execute(
            "SELECT recorded_date FROM external_signals WHERE signal_type = 'holiday'"
        ).fetchall()
        is_holiday_window = 1 if any(
            abs((datetime.fromisoformat(h[0]).date() - now.date()).days) <= 2
            for h in holiday_dates
        ) else 0

        context = {
            "route": route,
            "flight_class": flight_class,
            "days_to_departure": days_to_departure,
            "current_price": base_fare,
            "base_fare": base_fare,
            "time_of_day": now.hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_holiday_window": is_holiday_window,
            "petrol_price": get_signal(conn, "petrol_price"),
            "diesel_price": get_signal(conn, "diesel_price"),
            "usd_to_pkr": get_signal(conn, "usd_to_pkr"),
            "competitor_min_price": comp_min,
            "competitor_avg_price": comp_avg,
            "price_vs_competitor_ratio": (base_fare / comp_avg if comp_avg else None),
            "competitor_data_is_real": comp_avg is not None,
            "is_international": route == "KHI-DXB",
        }

        result = optimize_price(context, total_seats, remaining_seats)

        return {
            "route": route,
            "flight_class": flight_class,
            "recommended_price": result.recommended_price,
            "expected_revenue": result.expected_revenue,
            "predicted_demand_ratio": result.predicted_demand_ratio,
            "candidates_evaluated": result.candidates_evaluated,
            "competitor_data_is_real": comp_avg is not None,
        }
    finally:
        conn.close()

def check_health() -> dict:
    db_ok = DB_PATH.exists()
    model_path = ROOT / "models" / "demand_model.pkl"
    model_ok = model_path.exists()
    return {
        "status": "ok" if (db_ok and model_ok) else "degraded",
        "database_connected": db_ok,
        "model_loaded": model_ok,
    }
