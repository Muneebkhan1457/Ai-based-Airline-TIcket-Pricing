"""
Fuel price scraper for the PIA dynamic pricing MVP.

Scrapes the current OGRA-notified petrol and diesel prices from
ograprices.com (a site that tracks official OGRA notifications).

Run this on a schedule (every 15 days matches OGRA's fortnightly
revision cycle, but it's safe to run daily since the scraper
simply re-saves the same value if nothing changed).

Output: raw/fuel_price_YYYY-MM-DD.json
"""

import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://ograprices.com/today-petrol-price/"
RAW_DIR = ROOT / "raw"
MIN_REASONABLE_FUEL_PRICE = 200
MAX_REASONABLE_FUEL_PRICE = 500
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def extract_prices(html: str) -> dict:
    """
    Pulls petrol and HSD (diesel) prices out of the Current Fuel Rates section.
    The page also contains nearby change indicators such as "Down Rs 0.75";
    those must not be treated as fuel prices.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    current_rates_match = re.search(
        r"Current Fuel Rates(?P<section>.*?)(?:Regulatory Insight|Latest OGRA|Fuel Price Trends)",
        text,
        flags=re.IGNORECASE,
    )
    search_text = current_rates_match.group("section") if current_rates_match else text

    petrol_match = re.search(
        r"\bPetrol\b\s+PKR\s+(\d{2,3}(?:\.\d{1,2})?)\s*/?\s*Litre",
        search_text,
        flags=re.IGNORECASE,
    )
    diesel_match = re.search(
        r"\b(?:High Speed Diesel|HSD)\b\s+PKR\s+(\d{2,3}(?:\.\d{1,2})?)\s*/?\s*Litre",
        search_text,
        flags=re.IGNORECASE,
    )

    if not petrol_match or not diesel_match:
        raise ValueError(
            "Could not find petrol/diesel prices in the Current Fuel Rates section. "
            "The site structure may have changed -- inspect the HTML manually."
        )

    petrol_price = float(petrol_match.group(1))
    diesel_price = float(diesel_match.group(1))

    for label, value in {
        "petrol_price_pkr_per_litre": petrol_price,
        "diesel_price_pkr_per_litre": diesel_price,
    }.items():
        if not MIN_REASONABLE_FUEL_PRICE <= value <= MAX_REASONABLE_FUEL_PRICE:
            raise ValueError(
                f"Rejected invalid {label}={value}; expected "
                f"{MIN_REASONABLE_FUEL_PRICE}-{MAX_REASONABLE_FUEL_PRICE} PKR/litre"
            )

    return {
        "petrol_price_pkr_per_litre": petrol_price,
        "diesel_price_pkr_per_litre": diesel_price,
    }


def save_snapshot(data: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = RAW_DIR / f"fuel_price_{today}.json"

    payload = {
        "scraped_date": today,
        "source": SOURCE_URL,
        **data,
    }

    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def main():
    html = fetch_page(SOURCE_URL)
    prices = extract_prices(html)
    out_path = save_snapshot(prices)
    print(f"Saved fuel price snapshot: {out_path}")
    print(prices)


if __name__ == "__main__":
    main()
