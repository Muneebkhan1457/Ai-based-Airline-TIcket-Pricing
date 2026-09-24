"""
migrate_sqlite_to_rds.py
========================
Yeh script local SQLite (Data_load/flight.db) ka saara data
AWS RDS PostgreSQL mein migrate karti hai.

Run karne ka tarika:
    uv run python scripts/migrate_sqlite_to_rds.py
"""

import sqlite3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file!")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: uv add psycopg2-binary")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQLITE_DB    = PROJECT_ROOT / "Data_load" / "flight.db"

if not SQLITE_DB.exists():
    print(f"ERROR: SQLite database not found at {SQLITE_DB}")
    sys.exit(1)

print(f"SQLite DB: {SQLITE_DB}")
print(f"Target:    {DATABASE_URL.split('@')[-1]}")
print()

sqlite_conn = sqlite3.connect(str(SQLITE_DB))
sqlite_conn.row_factory = sqlite3.Row

dsn = DATABASE_URL if "sslmode" in DATABASE_URL else DATABASE_URL + "?sslmode=require"
pg_conn = psycopg2.connect(dsn)
pg_conn.autocommit = False
pg_cur = pg_conn.cursor()

print("Connected to SQLite and AWS RDS PostgreSQL successfully!")
print()

print("Step 1: Creating tables in PostgreSQL...")

pg_cur.execute("""
CREATE TABLE IF NOT EXISTS flights (
    id                SERIAL PRIMARY KEY,
    route             TEXT NOT NULL,
    origin            TEXT,
    destination       TEXT,
    flight_class      TEXT,
    days_to_departure INTEGER,
    current_price     REAL,
    total_seats       INTEGER,
    booked_seats      INTEGER,
    remaining_seats   INTEGER
);
""")

pg_cur.execute("""
CREATE TABLE IF NOT EXISTS external_signals (
    id            SERIAL PRIMARY KEY,
    route         TEXT,
    signal_type   TEXT NOT NULL,
    value         REAL NOT NULL,
    unit          TEXT,
    source        TEXT,
    recorded_date TEXT NOT NULL,
    scraped_at    TEXT NOT NULL,
    UNIQUE (route, signal_type, recorded_date)
);
""")

pg_cur.execute("""
CREATE TABLE IF NOT EXISTS price_history (
    id                      SERIAL PRIMARY KEY,
    route                   TEXT NOT NULL,
    flight_class            TEXT NOT NULL,
    price                   REAL NOT NULL,
    expected_revenue        REAL,
    predicted_demand_ratio  REAL,
    trigger_reason          TEXT,
    recorded_at             TEXT NOT NULL
);
""")

pg_conn.commit()
print("   Tables created!")
print()

print("Step 2: Migrating flights table...")
sqlite_rows = sqlite_conn.execute("""
    SELECT route, origin, destination, flight_class,
           days_to_departure, current_price, total_seats,
           booked_seats, remaining_seats
    FROM flights
""").fetchall()

if sqlite_rows:
    psycopg2.extras.execute_values(
        pg_cur,
        """INSERT INTO flights
           (route, origin, destination, flight_class, days_to_departure,
            current_price, total_seats, booked_seats, remaining_seats)
           VALUES %s ON CONFLICT DO NOTHING""",
        [tuple(r) for r in sqlite_rows],
        page_size=500,
    )
    pg_conn.commit()
    print(f"   {len(sqlite_rows):,} flights migrated!")
else:
    print("   No flight rows found.")
print()

print("Step 3: Migrating external_signals table...")
signal_rows = sqlite_conn.execute("""
    SELECT route, signal_type, value, unit, source, recorded_date, scraped_at
    FROM external_signals
""").fetchall()

if signal_rows:
    psycopg2.extras.execute_values(
        pg_cur,
        """INSERT INTO external_signals
           (route, signal_type, value, unit, source, recorded_date, scraped_at)
           VALUES %s
           ON CONFLICT (route, signal_type, recorded_date) DO NOTHING""",
        [tuple(r) for r in signal_rows],
        page_size=500,
    )
    pg_conn.commit()
    print(f"   {len(signal_rows):,} signal entries migrated!")
else:
    print("   No signal rows found.")
print()

print("Step 4: Migrating price_history table...")
history_rows = sqlite_conn.execute("""
    SELECT route, flight_class, price, expected_revenue,
           predicted_demand_ratio, trigger_reason, recorded_at
    FROM price_history
""").fetchall()

if history_rows:
    psycopg2.extras.execute_values(
        pg_cur,
        """INSERT INTO price_history
           (route, flight_class, price, expected_revenue,
            predicted_demand_ratio, trigger_reason, recorded_at)
           VALUES %s""",
        [tuple(r) for r in history_rows],
        page_size=500,
    )
    pg_conn.commit()
    print(f"   {len(history_rows):,} price history rows migrated!")
else:
    print("   No price_history rows found.")
print()

print("Step 5: Verifying row counts...")
print(f"   {'Table':<22} {'SQLite':>10} {'PostgreSQL':>12} {'Match':>8}")
print(f"   {'-'*52}")

all_ok = True
for table in ["flights", "external_signals", "price_history"]:
    sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
    pg_count = pg_cur.fetchone()[0]
    match = "OK" if sqlite_count == pg_count else "MISMATCH"
    if sqlite_count != pg_count:
        all_ok = False
    print(f"   {table:<22} {sqlite_count:>10,} {pg_count:>12,} {match:>8}")

print()
if all_ok:
    print("Migration COMPLETE! All row counts match. Data is live on AWS RDS!")
else:
    print("Some row counts do not match. Please check the output above.")

sqlite_conn.close()
pg_cur.close()
pg_conn.close()
