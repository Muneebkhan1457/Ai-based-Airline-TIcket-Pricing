"""
Database verification script for the PIA dynamic pricing MVP.

Prints a full picture of what's actually stored in flight.db:
- every table and its row count
- a sample of rows from each table
- a breakdown of external_signals by signal_type

Run from the project root:
    uv run python check_tables.py       (already exists, lighter version)
    uv run python verify_database.py    (this one, full detail)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "flight.db"


def get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall()
    return [r[0] for r in rows]


def print_table_summary(conn: sqlite3.Connection, table: str) -> None:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"\n{'=' * 60}")
    print(f"TABLE: {table}  |  ROWS: {count}")
    print("=" * 60)

    if count == 0:
        print("  (empty)")
        return

    cols = [d[1] for d in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    print(f"  Columns: {', '.join(cols)}")

    print("  Sample rows:")
    for row in conn.execute(f"SELECT * FROM {table} LIMIT 5").fetchall():
        print(f"    {row}")


def print_signal_breakdown(conn: sqlite3.Connection) -> None:
    tables = get_tables(conn)
    if "external_signals" not in tables:
        return

    print(f"\n{'=' * 60}")
    print("external_signals BREAKDOWN BY signal_type")
    print("=" * 60)
    rows = conn.execute(
        """
        SELECT signal_type, COUNT(*), MIN(recorded_date), MAX(recorded_date)
        FROM external_signals
        GROUP BY signal_type
        ORDER BY signal_type
        """
    ).fetchall()
    for signal_type, count, min_date, max_date in rows:
        print(f"  {signal_type:30s} count={count:<5} date range: {min_date} to {max_date}")


def main():
    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    tables = get_tables(conn)

    print(f"Database: {DB_PATH}")
    print(f"Tables found: {tables}")

    for table in tables:
        print_table_summary(conn, table)

    print_signal_breakdown(conn)

    conn.close()


if __name__ == "__main__":
    main()