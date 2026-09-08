"""
Loads Pakistan's 2026 public holiday calendar into external_signals.

These are official dates from Cabinet Division notifications (not
scraped live — holiday calendars are published once per year and
don't need repeated scraping like fuel/competitor prices do).

Stored as signal_type="holiday", value=1 (a flag), with the holiday
name in the `source` field.

Run from the project root:
    uv run python etl\\load_holidays.py
"""

import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "flight.db"

# Official 2026 Pakistan public holidays (Cabinet Division notification).
# Islamic dates (marked *) are subject to moon sighting and may shift by
# 1-2 days from what was notified in advance.
HOLIDAYS_2026 = [
    (date(2026, 2, 5), "Kashmir Day"),
    (date(2026, 3, 21), "Eid-ul-Fitr Day 1"),
    (date(2026, 3, 22), "Eid-ul-Fitr Day 2"),
    (date(2026, 3, 23), "Eid-ul-Fitr Day 3 / Pakistan Day"),
    (date(2026, 5, 1), "Labour Day"),
    (date(2026, 5, 27), "Eid-ul-Azha Day 1"),
    (date(2026, 5, 28), "Eid-ul-Azha Day 2 / Youm-e-Takbeer"),
    (date(2026, 5, 29), "Eid-ul-Azha Day 3"),
    (date(2026, 6, 25), "Ashura (9th Muharram)"),
    (date(2026, 6, 26), "Ashura (10th Muharram)"),
    (date(2026, 8, 14), "Independence Day"),
    (date(2026, 8, 25), "Eid Milad-un-Nabi"),
    (date(2026, 9, 6), "Defence Day"),
    (date(2026, 11, 9), "Allama Iqbal Day"),
    (date(2026, 12, 25), "Quaid-e-Azam Day / Christmas"),
]

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


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()

    today = date.today().isoformat()
    inserted = 0

    for holiday_date, name in HOLIDAYS_2026:
        row = (
            "GLOBAL",  # holidays are a global signal, not tied to a route
            "holiday",
            1.0,  # flag value: 1 = this date is a holiday
            None,
            name,
            holiday_date.isoformat(),
            today,
        )
        cursor = conn.execute(INSERT_SQL, row)
        if cursor.rowcount == 1:
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Inserted {inserted} new holiday rows (out of {len(HOLIDAYS_2026)} total)")


if __name__ == "__main__":
    main()
