"""
Compares the latest external_signals values against the previously
known values (kept in memory between scheduler runs) to decide whether
a recalculation should fire — the OR-logic trigger discussed in the
project's architecture: ANY changed factor fires recalculation, but
the recalculation itself always uses the FULL current feature set.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"

_last_known_signals = {}  # in-memory cache between scheduler runs

def get_current_signals(conn) -> dict:
    rows = conn.execute(
        "SELECT route, signal_type, value FROM external_signals "
        "WHERE recorded_date = (SELECT MAX(recorded_date) FROM external_signals)"
    ).fetchall()
    return {(route, signal_type): value for route, signal_type, value in rows}

def check_for_changes() -> dict:
    """
    Returns {"changed": bool, "changed_keys": [...], "affected_routes": set(...)}
    """
    global _last_known_signals
    conn = sqlite3.connect(DB_PATH)
    current = get_current_signals(conn)
    conn.close()

    changed_keys = []
    for key, value in current.items():
        if key not in _last_known_signals or _last_known_signals[key] != value:
            changed_keys.append(key)

    affected_routes = {route for (route, signal_type) in changed_keys if route is not None}
    # global signals (route=None, e.g. fuel/FX) affect ALL routes
    global_changed = any(route is None for (route, signal_type) in changed_keys)

    _last_known_signals = current

    return {
        "changed": len(changed_keys) > 0,
        "changed_keys": changed_keys,
        "affected_routes": affected_routes,
        "global_changed": global_changed,
    }
