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
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PETROL_URL = "https://ograprices.com/today-petrol-price/"
DIESEL_URL = "https://ograprices.com/today-diesel-price/"
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


def extract_price_from_html(html: str, fuel_type: str) -> float:
    """
    Pulls price out of the fpp-solo-price widget for a specific fuel type.
    """
    soup = BeautifulSoup(html, "html.parser")

    for name_tag in soup.find_all("h3", class_="fpp-solo-name"):
        name_text = name_tag.get_text(strip=True).lower()
        if fuel_type in name_text:
            price_div = name_tag.find_next_sibling("div", class_="fpp-solo-price")
            if price_div:
                counter = price_div.find("span", class_="fpp-counter")
                if counter and counter.has_attr("data-target"):
                    return float(counter["data-target"])
    return None


def extract_prices() -> dict:
    petrol_html = fetch_page(PETROL_URL)
    diesel_html = fetch_page(DIESEL_URL)

    petrol_price = extract_price_from_html(petrol_html, "petrol")
    diesel_price = extract_price_from_html(diesel_html, "diesel")
    if diesel_price is None:
        diesel_price = extract_price_from_html(diesel_html, "hsd")

    if petrol_price is None or diesel_price is None:
        raise ValueError(
            f"Could not find petrol/diesel prices (Petrol: {petrol_price}, Diesel: {diesel_price}). "
            "The site structure may have changed -- inspect the HTML manually."
        )

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
        "source": f"{PETROL_URL} / {DIESEL_URL}",
        **data,
    }

    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def main():
    prices = extract_prices()
    out_path = save_snapshot(prices)
    print(f"Saved fuel price snapshot: {out_path}")
    print(prices)


if __name__ == "__main__":
    main()
