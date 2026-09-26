import os
import sqlite3
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "flight.db"

try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


def get_connection(db_path: Optional[Path | str] = None):
    """Return (conn, is_postgres).
    If db_path is explicitly provided, always connects to that SQLite file.
    Otherwise checks DATABASE_URL for AWS RDS PostgreSQL.
    """
    if db_path is not None:
        return sqlite3.connect(str(db_path)), False

    db_url = os.getenv("DATABASE_URL")
    if db_url and _PSYCOPG2_AVAILABLE:
        dsn = db_url if "sslmode" in db_url else db_url + "?sslmode=require"
        conn = psycopg2.connect(dsn)
        return conn, True
    else:
        return sqlite3.connect(str(DEFAULT_DB_PATH)), False


def insert_signals(conn, is_postgres: Optional[bool] = None, rows: list = None) -> int:
    """Insert signals with duplicate handling into either PostgreSQL or SQLite."""
    if not rows:
        return 0

    if is_postgres is None:
        is_postgres = not isinstance(conn, sqlite3.Connection)

    inserted = 0
    if is_postgres:
        sql = """
        INSERT INTO external_signals (
            route, signal_type, value, unit, source, recorded_date, scraped_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (route, signal_type, recorded_date)
        DO UPDATE SET value = EXCLUDED.value, scraped_at = EXCLUDED.scraped_at;
        """
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(
                    sql,
                    (
                        r["route"],
                        r["signal_type"],
                        r["value"],
                        r["unit"],
                        r["source"],
                        r["recorded_date"],
                        r["scraped_at"],
                    ),
                )
                inserted += 1
        conn.commit()
    else:
        sql = """
        INSERT OR REPLACE INTO external_signals (
            route, signal_type, value, unit, source, recorded_date, scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        for r in rows:
            conn.execute(
                sql,
                (
                    r["route"],
                    r["signal_type"],
                    r["value"],
                    r["unit"],
                    r["source"],
                    r["recorded_date"],
                    r["scraped_at"],
                ),
            )
            inserted += 1
        conn.commit()
    return inserted
