"""
Loads USD-PKR FX rate snapshots into the external_signals table in PostgreSQL (RDS) or SQLite (flight.db).
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


def load_fx_snapshot(raw_path: Path, conn, is_postgres: bool) -> int:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    rows = [
        {
            "route": "GLOBAL",
            "signal_type": "usd_to_pkr",
            "value": float(payload["usd_to_pkr"]),
            "unit": "PKR",
            "source": payload.get("source"),
            "recorded_date": payload["scraped_date"],
            "scraped_at": payload["scraped_date"],
        }
    ]

    return insert_signals(conn, is_postgres, rows)


def main():
    conn, is_postgres = get_connection()
    if not is_postgres:
        ensure_table(conn)

    fx_files = sorted(RAW_DIR.glob("fx_rate_*.json"))
    if not fx_files:
        print(f"No fx_rate_*.json files found in {RAW_DIR}")
        conn.close()
        return

    target = "AWS RDS PostgreSQL" if is_postgres else "local SQLite"
    total_inserted = 0
    for file_path in fx_files:
        inserted = load_fx_snapshot(file_path, conn, is_postgres)
        print(f"{file_path.name}: {inserted} row(s) processed into {target}")
        total_inserted += inserted

    conn.close()
    print(f"Done. Total FX rows processed: {total_inserted}")


if __name__ == "__main__":
    main()
