"""
Mock competitor price scraper for Sastaticket.pk.

Returns realistic mock data to avoid requiring Playwright inside the MVP Docker container.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"

ROUTES = [
    ("Karachi", "Lahore", "KHI-LHE"),
    ("Karachi", "Islamabad", "KHI-ISB"),
]

SEARCH_DAYS_AHEAD = 14
KNOWN_AIRLINES = ["PIA", "Airblue", "Serene Air", "Air Sial", "Fly Jinnah"]

def generate_mock_results(route_code: str) -> list[dict]:
    results = []
    base_price = 15000 if route_code == "KHI-LHE" else 20000
    
    # Generate 3-5 random competitors
    num_competitors = random.randint(3, 5)
    for _ in range(num_competitors):
        airline = random.choice(KNOWN_AIRLINES)
        # Price variation between -10% and +20%
        variation = random.uniform(-0.1, 0.2)
        price_pkr = round(base_price * (1 + variation), -2)  # Round to nearest 100
        
        results.append({
            "airline": airline,
            "price_pkr": float(price_pkr),
        })
    return results


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    travel_date = date.today() + timedelta(days=SEARCH_DAYS_AHEAD)
    today = date.today().isoformat()

    snapshot = {
        "scraped_date": today,
        "search_date": travel_date.isoformat(),
        "source": "https://www.sastaticket.pk (MOCKED)",
        "routes": {},
    }

    for origin, destination, route_code in ROUTES:
        print(f"Mock Scraping {route_code} ({origin} -> {destination})...")
        results = generate_mock_results(route_code)
        snapshot["routes"][route_code] = results
        print(f"  Found {len(results)} mock fares")

    out_path = RAW_DIR / f"competitor_prices_{today}.json"
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"Saved mock snapshot: {out_path}")


if __name__ == "__main__":
    main()