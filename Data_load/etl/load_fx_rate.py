"""
Loads USD-PKR FX rate snapshots into the external_signals table in flight.db.

Run from the project root:
    uv run python etl\\load_fx_rate.py
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


def load_fx_snapshot(raw_path: Path, conn: sqlite3.Connection) -> int:
    payload = json.loads(raw_path.read_text())

    row = (
        "GLOBAL",  # FX rate is a global signal, not tied to a route
        "usd_to_pkr",
        float(payload["usd_to_pkr"]),
        "PKR",
        payload.get("source"),
        payload["scraped_date"],
        payload["scraped_date"],
    )

    cursor = conn.execute(INSERT_SQL, row)
    conn.commit()
    return cursor.rowcount


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_table(conn)

    fx_files = sorted(RAW_DIR.glob("fx_rate_*.json"))
    if not fx_files:
        print(f"No fx_rate_*.json files found in {RAW_DIR}")
        return

    total_inserted = 0
    for file_path in fx_files:
        inserted = load_fx_snapshot(file_path, conn)
        print(f"{file_path.name}: {inserted} new row(s)")
        total_inserted += inserted

    conn.close()
    print(f"Done. Total new rows inserted: {total_inserted}")


if __name__ == "__main__":
    main()
