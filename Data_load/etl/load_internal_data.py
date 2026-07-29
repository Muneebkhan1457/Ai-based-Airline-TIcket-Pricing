"""
Loads the Kaggle-derived, PIA-style internal flight dataset into the
`flights` table in flight.db.

The full dataset has 300k+ rows, which is more than an MVP demo needs
for training/testing speed, so this script takes a random sample
(default 15,000 rows) before loading.

Run from the project root:
    uv run python etl\\load_internal_data.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "flight.db"
CSV_PATH = ROOT / "internal" / "generated" / "flights_internal.csv"

SAMPLE_SIZE = 15000
RANDOM_SEED = 42  # fixed seed so the sample is reproducible across runs

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    origin TEXT,
    destination TEXT,
    flight_class TEXT,
    days_to_departure INTEGER,
    current_price REAL,
    total_seats INTEGER,
    booked_seats INTEGER,
    remaining_seats INTEGER
);
"""

INSERT_SQL = """
INSERT INTO flights (
    route, origin, destination, flight_class,
    days_to_departure, current_price, total_seats,
    booked_seats, remaining_seats
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()


def load_sample(csv_path: Path, sample_size: int) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    print(f"Full dataset: {len(df)} rows")
    sample = df.sample(n=min(sample_size, len(df)), random_state=RANDOM_SEED)
    print(f"Sampled: {len(sample)} rows")
    return sample


def insert_rows(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    rows = [
        (
            r["route"], r["origin"], r["destination"], r["flight_class"],
            int(r["days_to_departure"]), float(r["price_pkr"]),
            int(r["total_seats"]), int(r["booked_seats"]), int(r["remaining_seats"]),
        )
        for _, r in df.iterrows()
    ]
    conn.executemany(INSERT_SQL, rows)
    conn.commit()
    return len(rows)


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH} not found. Run internal\\prepare_internal_data.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    ensure_table(conn)

    sample = load_sample(CSV_PATH, SAMPLE_SIZE)
    inserted = insert_rows(conn, sample)

    conn.close()
    print(f"Inserted {inserted} rows into flights table in {DB_PATH}")


if __name__ == "__main__":
    main()