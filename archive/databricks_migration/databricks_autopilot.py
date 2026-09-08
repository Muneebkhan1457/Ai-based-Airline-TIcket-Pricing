"""
Autopilot scheduler for the Databricks-backed pricing system.

Flow (every N minutes):
  1. Run the existing local scrapers + ETL (writes to local flight.db, unchanged).
  2. Push newly-scraped signals to the Databricks external_signals table.
  3. Delta-check latest signals vs last-known values (in-memory).
  4. If anything changed, reprice affected routes using the MLflow model
     and persist results to the Databricks price_history table.

This keeps the local scrapers/ETL exactly as they were ("don't change anything")
while making the Databricks tables + MLflow model the system of record.
"""
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from api import services
from scheduler.jobs import run_fuel_job, run_competitor_job, run_fx_job, init_db

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"
CHECK_INTERVAL_MINUTES = 10

_last_known_signals = {}


def get_local_signals() -> list[dict]:
    """Read all rows from the local external_signals table."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT route, signal_type, value, unit, source, recorded_date
           FROM external_signals"""
    ).fetchall()
    conn.close()
    return [
        {
            "route": r[0],
            "signal_type": r[1],
            "value": float(r[2]),
            "unit": r[3],
            "source": r[4],
            "recorded_date": r[5],
        }
        for r in rows
    ]


def _norm_date(value) -> str:
    """Normalize a recorded_date (str or datetime) to a YYYY-MM-DD string."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _existing_signal_keys() -> set[tuple]:
    """Set of (route, signal_type, recorded_date) already in Databricks."""
    cursor = services._get_connection().cursor()
    cursor.execute(
        "SELECT route, signal_type, recorded_date FROM airline_daw.pia_pricing.external_signals"
    )
    rows = cursor.fetchall()
    cursor.close()
    return {
        (r[0], r[1], _norm_date(r[2]))
        for r in rows
    }


def push_signals_to_databricks() -> int:
    """Push local signals whose (route, signal_type, recorded_date) is not yet in Databricks."""
    existing = _existing_signal_keys()
    cursor = services._get_connection().cursor()

    signals = get_local_signals()
    pushed = 0
    for sig in signals:
        key = (sig["route"], sig["signal_type"], _norm_date(sig["recorded_date"]))
        if key in existing:
            continue
        cursor.execute(
            """INSERT INTO airline_daw.pia_pricing.external_signals
               (route, signal_type, value, unit, source, recorded_date, scraped_at)
               VALUES (?, ?, ?, ?, ?, CAST(? AS TIMESTAMP), CURRENT_DATE)""",
            (
                sig["route"], sig["signal_type"], sig["value"],
                sig["unit"], sig["source"], sig["recorded_date"],
            ),
        )
        existing.add(key)
        pushed += 1

    cursor.close()
    services._get_connection().commit()
    return pushed


def run_etl_and_push() -> int:
    """Run local scrapers + ETL, then mirror fresh signals to Databricks."""
    init_db()
    run_fuel_job()
    run_competitor_job()
    run_fx_job()
    return push_signals_to_databricks()


def _latest_databricks_signals() -> dict:
    """Latest snapshot of signals from Databricks keyed by (route, signal_type).

    Uses the most recent recorded_date per (route, signal_type) so that e.g. a
    future pre-loaded holiday (12-25) does not mask a fresh fuel-price change.
    """
    cursor = services._get_connection().cursor()
    cursor.execute(
        """SELECT route, signal_type, value FROM (
               SELECT route, signal_type, value,
                      ROW_NUMBER() OVER (PARTITION BY route, signal_type
                                         ORDER BY recorded_date DESC) AS rn
               FROM airline_daw.pia_pricing.external_signals
           ) WHERE rn = 1"""
    )
    rows = cursor.fetchall()
    cursor.close()
    return {(r[0], r[1]): r[2] for r in rows}


def check_for_changes() -> dict:
    """OR-logic delta check (same as local scheduler/delta_check.py)."""
    global _last_known_signals
    current = _latest_databricks_signals()

    changed_keys = [
        key for key, value in current.items()
        if key not in _last_known_signals or _last_known_signals[key] != value
    ]

    affected_routes = {
        route for (route, _st) in changed_keys
        if route and route != "GLOBAL"
    }
    global_changed = any(
        route in (None, "GLOBAL") for (route, _st) in changed_keys
    )

    _last_known_signals = current

    return {
        "changed": len(changed_keys) > 0,
        "changed_keys": changed_keys,
        "affected_routes": affected_routes,
        "global_changed": global_changed,
    }


def scheduled_check():
    """One full autopilot cycle."""
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Running scheduled signal check...")
    try:
        pushed = run_etl_and_push()
        print(f"  Signals pushed to Databricks: {pushed}")
    except Exception as e:
        print(f"  Warning: scraper/ETL/push failed ({e}) - continuing with existing data")

    delta = check_for_changes()
    if not delta["changed"]:
        print("  No market changes detected. Prices remain unchanged.")
        return

    print(f"  Change detected: {delta['changed_keys']}")
    routes = delta["affected_routes"]
    if delta["global_changed"]:
        routes = set(services.ROUTES)

    routes = routes & set(services.ROUTES)
    if not routes:
        print("  No repricable routes affected.")
        return

    for route in sorted(routes):
        print(f"  Repricing {route}...")
        _reprice_route(route)


def _reprice_route(route: str):
    """Reprice one route across all classes and persist to price_history."""
    records = []
    for flight_class in services.CLASSES:
        flight = services.get_representative_flight(route, flight_class)
        if flight is None:
            continue
        base_fare = services.get_base_fare(route, flight_class)
        if base_fare is None:
            continue

        context = services._build_context(
            route, flight_class, flight["days_to_departure"],
            flight["total_seats"], flight["remaining_seats"],
            flight["current_price"], base_fare,
        )
        result = services.optimize_price(context, flight["total_seats"], flight["remaining_seats"])
        records.append({
            "route": route,
            "flight_class": flight_class,
            "recommended_price": result["recommended_price"],
            "expected_revenue": result["expected_revenue"],
            "predicted_demand_ratio": result["predicted_demand_ratio"],
            "trigger_reason": "delta_trigger",
            "recorded_at": datetime.now().isoformat(),
        })
        print(f"  [{route}/{flight_class}] price: {result['recommended_price']} PKR")

    if records:
        services.insert_price_history(records)


def main():
    from apscheduler.schedulers.blocking import BlockingScheduler

    services.ensure_schema()
    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_check, "interval", minutes=CHECK_INTERVAL_MINUTES,
        next_run_time=datetime.now(),
    )
    print(f"Autopilot started (Databricks backend). Checking every {CHECK_INTERVAL_MINUTES} minutes. Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Autopilot stopped.")


if __name__ == "__main__":
    main()

