"""One-time cleanup for duplicated global external_signals rows."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "flight.db"
GLOBAL_SIGNAL_TYPES = ("petrol_price", "diesel_price", "usd_to_pkr")
GLOBAL_OR_NULL_SIGNAL_TYPES = (*GLOBAL_SIGNAL_TYPES, "holiday")
BAD_PETROL_ROW_ID = 172


def delete_bad_petrol_row(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        """
        DELETE FROM external_signals
        WHERE id = ?
          AND signal_type = 'petrol_price'
          AND value = 4.08
          AND recorded_date = '2026-08-04'
        """,
        (BAD_PETROL_ROW_ID,),
    )
    return cursor.rowcount


def delete_duplicates_for_signal(conn: sqlite3.Connection, signal_type: str) -> int:
    cursor = conn.execute(
        """
        DELETE FROM external_signals
        WHERE signal_type = ?
          AND id NOT IN (
              SELECT MIN(id)
              FROM external_signals
              WHERE signal_type = ?
              GROUP BY recorded_date
          )
        """,
        (signal_type, signal_type),
    )
    return cursor.rowcount


def migrate_global_routes(conn: sqlite3.Connection) -> int:
    placeholders = ",".join("?" for _ in GLOBAL_OR_NULL_SIGNAL_TYPES)
    cursor = conn.execute(
        f"""
        UPDATE external_signals
        SET route = 'GLOBAL'
        WHERE signal_type IN ({placeholders})
          AND route IS NULL
        """,
        GLOBAL_OR_NULL_SIGNAL_TYPES,
    )
    return cursor.rowcount


def count_duplicate_dates(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    placeholders = ",".join("?" for _ in GLOBAL_SIGNAL_TYPES)
    return conn.execute(
        f"""
        SELECT signal_type, recorded_date, COUNT(*) AS row_count
        FROM external_signals
        WHERE signal_type IN ({placeholders})
        GROUP BY signal_type, recorded_date
        HAVING COUNT(*) > 1
        ORDER BY signal_type, recorded_date
        """,
        GLOBAL_SIGNAL_TYPES,
    ).fetchall()


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"Database: {DB_PATH}")
        bad_deleted = delete_bad_petrol_row(conn)
        print(f"Deleted bad petrol row id={BAD_PETROL_ROW_ID}: {bad_deleted}")

        for signal_type in GLOBAL_SIGNAL_TYPES:
            removed = delete_duplicates_for_signal(conn, signal_type)
            print(f"Removed duplicate rows for {signal_type}: {removed}")

        migrated = migrate_global_routes(conn)
        print(f"Migrated remaining global NULL routes to GLOBAL: {migrated}")

        remaining_duplicates = count_duplicate_dates(conn)
        print(f"Remaining duplicate global signal/date groups: {len(remaining_duplicates)}")
        for row in remaining_duplicates:
            print(row)

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
