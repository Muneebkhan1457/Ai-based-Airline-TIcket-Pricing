"""
Wrapper functions that run each scraper + its ETL loader as a single job,
so the scheduler can call one function per data source instead of
juggling scraper/ETL pairs directly.
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"

def init_db():
    """Ensure price_history table exists in flight.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route TEXT NOT NULL,
        flight_class TEXT NOT NULL,
        price REAL NOT NULL,
        expected_revenue REAL,
        predicted_demand_ratio REAL,
        trigger_reason TEXT,
        recorded_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def run_fuel_job():
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "scrapers" / "scrap_fuel_price.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "etl" / "load_to_db.py")], check=True)

def run_competitor_job():
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "scrapers" / "scrape_competitor_prices.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "etl" / "load_competitor_prices.py")], check=True)

def run_fx_job():
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "scrapers" / "fetch_fx_rate.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "Data_load" / "etl" / "load_fx_rate.py")], check=True)

if __name__ == "__main__":
    init_db()
    print("Database initialized with price_history table.")
