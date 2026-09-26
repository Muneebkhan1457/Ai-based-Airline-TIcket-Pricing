"""
Loads competitor price data scraped from Sastaticket.pk into the
external_signals table in PostgreSQL (RDS) or SQLite (flight.db).
"""

import json
import sqlite3
import sys
from pathlib import Path

try:
    from db import get_connection, insert_signals
except ImportError:
    from Data_load.etl.db import get_connection, insert_signals

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "flight.db"
RAW_DIR = ROOT / "raw"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS external_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT,
    signal_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    source TEXT,
    recorded_date TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    UNIQUE(route, signal_type, recorded_date)
);
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()


def load_competitor_snapshot(raw_path: Path, conn=None) -> int:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    if "routes" not in payload:
        print(f"  Skipping {raw_path.name}: old format (no 'routes' key)")
        return 0

    close_conn = False
    if conn is None:
        conn, is_postgres = get_connection()
        close_conn = True
    else:
        is_postgres = not isinstance(conn, sqlite3.Connection)

    recorded_date = payload["scraped_date"]

    rows = []
    for route, fares in payload["routes"].items():
        for idx, fare in enumerate(fares, start=1):
            airline = fare.get("airline", "Unknown")
            price = fare.get("price_pkr")
            if price is None:
                continue

            rows.append(
                {
                    "route": route,
                    "signal_type": f"competitor_price_{idx}",
                    "value": float(price),
                    "unit": "PKR",
                    "source": f"sastaticket:{airline}",
                    "recorded_date": recorded_date,
                    "scraped_at": payload.get("scraped_date"),
                }
            )

    try:
        return insert_signals(conn, is_postgres, rows)
    finally:
        if close_conn:
            conn.close()


def main():
    conn, is_postgres = get_connection()
    if not is_postgres:
        ensure_table(conn)

    competitor_files = sorted(RAW_DIR.glob("competitor_prices_*.json"))
    if not competitor_files:
        print(f"No competitor_prices_*.json files found in {RAW_DIR}")
        conn.close()
        return

    target = "AWS RDS PostgreSQL" if is_postgres else "SQLite"
    total_inserted = 0
    for file_path in competitor_files:
        inserted = load_competitor_snapshot(file_path, conn)
        print(f"{file_path.name}: {inserted} row(s) processed into {target}")
        total_inserted += inserted

    conn.close()
    print(f"Done. Total competitor rows processed: {total_inserted}")


if __name__ == "__main__":
    main()