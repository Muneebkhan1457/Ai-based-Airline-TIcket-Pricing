import json
import sqlite3
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "flight.db"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
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
        )
        """
    )
    conn.commit()


def load_fuel_price_snapshot(
    raw_path: Path | str,
    db_path: Optional[Path | str] = None,
) -> list[dict]:
    raw_path = Path(raw_path)

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    with raw_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    conn = sqlite3.connect(db_path)

    try:
        ensure_schema(conn)

        rows = []

        fuel_prices = {
            "petrol_price": payload.get("petrol_price_pkr_per_litre"),
            "diesel_price": payload.get("diesel_price_pkr_per_litre"),
        }

        for signal_type, value in fuel_prices.items():
            if value is None:
                continue
            value = float(value)
            if not 200 <= value <= 500:
                print(f"Skipping invalid {signal_type}={value}; expected 200-500 PKR/litre")
                continue

            rows.append(
                {
                    "route": "GLOBAL",
                    "signal_type": signal_type,
                    "value": value,
                    "unit": "PKR/litre",
                    "source": payload.get("source", "Unknown"),
                    "recorded_date": payload.get("scraped_date"),
                    "scraped_at": payload.get("scraped_date", payload.get("date")),
                }
            )

        inserted = 0

        for row in rows:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO external_signals (
                    route,
                    signal_type,
                    value,
                    unit,
                    source,
                    recorded_date,
                    scraped_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["route"],
                    row["signal_type"],
                    row["value"],
                    row["unit"],
                    row["source"],
                    row["recorded_date"],
                    row["scraped_at"],
                ),
            )

            if cursor.rowcount == 1:
                inserted += 1

        conn.commit()

        print(f"Inserted {inserted} new rows from {raw_path.name}")

        return rows

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    raw_dir = ROOT / "raw"

    if not raw_dir.exists():
        print(f"Directory not found: {raw_dir}")
        sys.exit(1)

    fuel_files = sorted(raw_dir.glob("fuel_price_*.json"))

    if not fuel_files:
        print(f"No fuel_price_*.json files found in {raw_dir}")
        sys.exit(1)

    for file_path in fuel_files:
        load_fuel_price_snapshot(file_path)
