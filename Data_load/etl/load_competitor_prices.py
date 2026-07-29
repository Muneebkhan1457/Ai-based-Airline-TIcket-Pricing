"""
Loads competitor price data scraped from Sastaticket.pk into the
external_signals table in flight.db.

The raw JSON has multiple fares per route (routes -> list of
{airline, price_pkr}). Since external_signals has a
UNIQUE(route, signal_type, recorded_date) constraint, each fare within
a route gets a position-based signal_type (competitor_price_1,
competitor_price_2, ...) so multiple fares for the same route/day don't
silently collide and get dropped. The airline name is preserved in the
`source` field instead of the signal_type, since airline detection from
the page text isn't always reliable ("Unknown" happens).

Run from the project root:
    uv run python etl\\load_competitor_prices.py
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "flight.db"
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

INSERT_SQL = """
INSERT OR IGNORE INTO external_signals (
    route, signal_type, value, unit, source, recorded_date, scraped_at
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()


def load_competitor_snapshot(raw_path: Path, conn: sqlite3.Connection) -> int:
    payload = json.loads(raw_path.read_text())

    if "routes" not in payload:
        print(f"  Skipping {raw_path.name}: old format (no 'routes' key)")
        return 0

    recorded_date = payload["scraped_date"]

    rows = []
    for route, fares in payload["routes"].items():
        for idx, fare in enumerate(fares, start=1):
            airline = fare.get("airline", "Unknown")
            price = fare.get("price_pkr")
            if price is None:
                continue

            rows.append(
                (
                    route,
                    f"competitor_price_{idx}",
                    float(price),
                    "PKR",
                    f"sastaticket:{airline}",
                    recorded_date,
                    payload.get("scraped_date"),
                )
            )

    inserted = 0
    for row in rows:
        cursor = conn.execute(INSERT_SQL, row)
        if cursor.rowcount == 1:
            inserted += 1

    conn.commit()
    return inserted


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_table(conn)

    competitor_files = sorted(RAW_DIR.glob("competitor_prices_*.json"))
    if not competitor_files:
        print(f"No competitor_prices_*.json files found in {RAW_DIR}")
        return

    total_inserted = 0
    for file_path in competitor_files:
        inserted = load_competitor_snapshot(file_path, conn)
        print(f"{file_path.name}: {inserted} new row(s)")
        total_inserted += inserted

    conn.close()
    print(f"Done. Total new rows inserted: {total_inserted}")


if __name__ == "__main__":
    main()