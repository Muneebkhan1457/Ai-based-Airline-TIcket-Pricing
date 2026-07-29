"""
FX rate fetcher for the PIA dynamic pricing MVP.
Pulls the current USD-PKR exchange rate from a free, no-signup API.
Output: raw/fx_rate_YYYY-MM-DD.json
"""

import json
from datetime import date
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"
API_URL = "https://open.er-api.com/v6/latest/USD"


def fetch_fx_rate() -> float:
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("result") != "success":
        raise ValueError(f"API did not return success: {data}")

    return data["rates"]["PKR"]


def save_snapshot(pkr_rate: float) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = RAW_DIR / f"fx_rate_{today}.json"

    payload = {
        "scraped_date": today,
        "source": API_URL,
        "usd_to_pkr": pkr_rate,
    }

    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def main():
    rate = fetch_fx_rate()
    out_path = save_snapshot(rate)
    print(f"USD to PKR rate: {rate}")
    print(f"Saved snapshot: {out_path}")


if __name__ == "__main__":
    main()