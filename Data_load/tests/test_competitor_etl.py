import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from etl.load_competitor_prices import ensure_table, load_competitor_snapshot


def test_load_competitor_snapshot_creates_route_rows(tmp_path):
    db_path = tmp_path / "test_flights.db"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "scraped_date": "2026-07-27",
        "routes": {
            "KHI-LHE": [
                {"airline": "Airblue", "price_pkr": 18500},
                {"airline": "SereneAir", "price_pkr": 17800},
            ]
        },
    }
    raw_path = raw_dir / "competitor_prices_2026-07-27.json"
    raw_path.write_text(json.dumps(payload), encoding="utf-8")

    conn = sqlite3.connect(db_path)
    ensure_table(conn)
    load_competitor_snapshot(raw_path, conn=conn)

    rows = conn.execute(
        "SELECT route, signal_type, value FROM external_signals ORDER BY signal_type"
    ).fetchall()
    conn.close()

    assert rows == [
        ("KHI-LHE", "competitor_price_1", 18500.0),
        ("KHI-LHE", "competitor_price_2", 17800.0),
    ]

