"""
The background daemon. Runs on an interval, re-scrapes signals, checks
for deltas, and triggers repricing only for affected routes when a
change is detected. Logs every action so autopilot behavior is visible.
"""
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.jobs import run_fuel_job, run_competitor_job, run_fx_job, init_db
from scheduler.delta_check import check_for_changes
from pricing_engine.optimizer import optimize_price

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"

CHECK_INTERVAL_MINUTES = 10  # MVP interval; real cadence differs per signal (see roadmap)

def get_base_fare(conn, route: str, flight_class: str):
    """Compute base_fare as AVG(current_price) grouped by route+class,
    matching the same logic used in models/prepare_dataset.py."""
    row = conn.execute(
        "SELECT AVG(current_price) FROM flights WHERE route = ? AND flight_class = ?",
        (route, flight_class)
    ).fetchone()
    return row[0] if row and row[0] is not None else None

def get_competitor_stats(conn, route: str):
    """Aggregate ALL competitor_price_* rows for a route (mirrors
    prepare_dataset.py's get_competitor_stats_by_route logic).
    Returns (competitor_min_price, competitor_avg_price) or (None, None)."""
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

def build_context_for_route(conn, route: str, flight_class: str) -> dict | None:
    """Pulls the latest known values for one route/class to build a
    prediction context — reads aggregate/representative values from DB."""
    flight_row = conn.execute(
        "SELECT * FROM flights WHERE route = ? AND flight_class = ? LIMIT 1",
        (route, flight_class)
    ).fetchone()
    if not flight_row:
        return None
    columns = [d[1] for d in conn.execute("PRAGMA table_info(flights)").fetchall()]
    flight = dict(zip(columns, flight_row))

    base_fare = get_base_fare(conn, route, flight_class)
    if base_fare is None:
        return None

    def get_signal(signal_type, route_filter=None):
        row = conn.execute(
            "SELECT value FROM external_signals WHERE signal_type = ? AND "
            "(route = ? OR route IS NULL) ORDER BY recorded_date DESC LIMIT 1",
            (signal_type, route_filter)
        ).fetchone()
        return row[0] if row else None

    comp_min, comp_avg = get_competitor_stats(conn, route)

    now = datetime.now()
    day_of_week = now.weekday()  # 0=Monday, 6=Sunday
    is_weekend = 1 if day_of_week >= 5 else 0

    holiday_dates = conn.execute(
        "SELECT recorded_date FROM external_signals WHERE signal_type = 'holiday'"
    ).fetchall()
    is_holiday_window = 1 if any(
        abs((datetime.fromisoformat(h[0]).date() - now.date()).days) <= 2
        for h in holiday_dates
    ) else 0

    return {
        "route": route,
        "flight_class": flight_class,
        "days_to_departure": flight["days_to_departure"],
        "current_price": flight["current_price"],
        "base_fare": base_fare,
        "time_of_day": now.hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_holiday_window": is_holiday_window,
        "petrol_price": get_signal("petrol_price"),
        "diesel_price": get_signal("diesel_price"),
        "usd_to_pkr": get_signal("usd_to_pkr"),
        "competitor_min_price": comp_min,
        "competitor_avg_price": comp_avg,
        "price_vs_competitor_ratio": (
            flight["current_price"] / comp_avg if comp_avg else None
        ),
        "competitor_data_is_real": comp_avg is not None,
        "is_international": route == "KHI-DXB",
    }, flight["total_seats"], flight["remaining_seats"]

def reprice_route(route: str):
    conn = sqlite3.connect(DB_PATH)
    for flight_class in ["Economy", "Business"]:
        built = build_context_for_route(conn, route, flight_class)
        if built is None:
            continue
        context, total_seats, remaining_seats = built
        if context["base_fare"] is None:
            continue

        result = optimize_price(context, total_seats, remaining_seats)

        conn.execute(
            "INSERT INTO price_history (route, flight_class, price, expected_revenue, "
            "predicted_demand_ratio, trigger_reason, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (route, flight_class, result.recommended_price, result.expected_revenue,
             result.predicted_demand_ratio, "delta_trigger", datetime.now(timezone.utc).isoformat())
        )
        print(f"  [{route}/{flight_class}] new price: {result.recommended_price} PKR "
              f"(expected revenue: {result.expected_revenue})")
    conn.commit()
    conn.close()

def scheduled_check():
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running scheduled signal check...")
    try:
        run_fuel_job()
        run_competitor_job()
        run_fx_job()
    except Exception as e:
        print(f"  Warning: a scraper job failed ({e}) — continuing with existing data")

    delta = check_for_changes()
    if not delta["changed"]:
        print("  No market changes detected. Prices remain unchanged.")
        return

    print(f"  Change detected: {delta['changed_keys']}")
    routes_to_reprice = delta["affected_routes"]
    if delta["global_changed"]:
        all_routes = ["KHI-LHE", "KHI-ISB", "KHI-DXB", "LHE-ISB", "KHI-PEW"]
        routes_to_reprice = set(all_routes)

    for route in routes_to_reprice:
        print(f"  Repricing {route}...")
        reprice_route(route)

def main():
    init_db()
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_check, "interval", minutes=CHECK_INTERVAL_MINUTES, next_run_time=datetime.now())
    print(f"Autopilot started. Checking every {CHECK_INTERVAL_MINUTES} minutes. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Autopilot stopped.")

if __name__ == "__main__":
    main()
