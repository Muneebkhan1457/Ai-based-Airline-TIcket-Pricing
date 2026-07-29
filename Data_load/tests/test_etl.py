import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from etl.load_to_db import load_fuel_price_snapshot


def test_load_fuel_price_snapshot_creates_signal_rows(tmp_path):
    db_path = tmp_path / "test_flights.db"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "scraped_date": "2026-07-27",
        "source": "https://example.com",
        "petrol_price_pkr_per_litre": 335.18,
        "diesel_price_pkr_per_litre": 383.46,
    }
    raw_path = raw_dir / "fuel_price_2026-07-27.json"
    raw_path.write_text(json.dumps(payload), encoding="utf-8")

    load_fuel_price_snapshot(raw_path, db_path=db_path)

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT signal_type, value, source, recorded_date FROM external_signals ORDER BY signal_type"
    ).fetchall()
    conn.close()

    assert rows == [
        ("diesel_price", 383.46, "https://example.com", "2026-07-27"),
        ("petrol_price", 335.18, "https://example.com", "2026-07-27"),
    ]
