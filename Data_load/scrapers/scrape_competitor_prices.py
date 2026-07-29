"""
Playwright-based competitor price scraper for Sastaticket.pk.

IMPORTANT: The selectors in this file (marked with TODO) are placeholders.
Sastaticket is a JavaScript-heavy site whose exact DOM structure can't be
verified without a live browser session against it. Use Playwright's
codegen tool to record the real flow and get accurate selectors:

    uv run playwright install chromium
    uv run playwright codegen https://www.sastaticket.pk

Manually perform a search in the recorder window (From/To/date/search),
then copy the generated selectors into the TODO spots below.

Output: raw/competitor_prices_YYYY-MM-DD.json
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"

# Routes to scrape: (origin_city, destination_city, route_code)
ROUTES = [
    ("Karachi", "Lahore", "KHI-LHE"),
    ("Karachi", "Islamabad", "KHI-ISB"),
]

SEARCH_DAYS_AHEAD = 14  # how many days from today to search a flight for


DESTINATION_AIRPORT_CODES = {
    "Lahore": "LHE",
    "Islamabad": "ISB",
}

KNOWN_AIRLINES = ["PIA", "Airblue", "Serene Air", "Air Sial", "Fly Jinnah"]


def scrape_route(page, origin: str, destination: str, travel_date: date) -> list[dict]:
    """
    Fills the search form for one route and extracts competitor prices
    from the results page.

    The search-form steps below are confirmed working (captured via
    Playwright codegen). The result-extraction steps still need real
    selectors — see the TODO markers, and the instructions in this
    file's docstring for how to capture them.
    """
    page.goto("https://www.sastaticket.pk/", timeout=30000)

    # dismiss the popup that appears on first load, if present
    try:
        page.get_by_role("button", name="Close").click(timeout=5000)
    except PWTimeout:
        pass

    page.get_by_role("textbox", name="Flying From (City or Airport)").click()
    page.get_by_role("textbox", name="Flying From (City or Airport)").fill(origin)
    page.get_by_role("textbox", name="Flying From (City or Airport)").press("Enter")
    print(f"    From filled: {origin}")

    page.get_by_role("textbox", name="Flying To (City or Airport)").fill(destination)
    dest_code = DESTINATION_AIRPORT_CODES.get(destination)
    if dest_code:
        try:
            page.locator(f'[data-test="search-fields-airport-option-{dest_code}"]').click(timeout=3000)
        except PWTimeout:
            page.get_by_role("textbox", name="Flying To (City or Airport)").press("Enter")
    else:
        page.get_by_role("textbox", name="Flying To (City or Airport)").press("Enter")
    print(f"    To filled: {destination}")

    # open the date picker calendar, then select the specific date
    try:
        page.locator('[data-test="search-fields-date-picker-departing"]').click(timeout=3000)
    except PWTimeout:
        pass  # calendar may already be open from a previous interaction

    date_str = travel_date.isoformat()  # e.g. "2026-08-12"
    page.locator(f'[data-test="search-fields-date-picker-calendar-date-{date_str}"]').click()
    print(f"    Date selected: {date_str}")

    page.get_by_role("button", name="Search flights").click()
    print("    Search clicked, waiting for results...")

    # NOTE: wait_for_load_state("networkidle") is intentionally NOT used here —
    # many modern sites (analytics, polling, chat widgets) never truly go idle,
    # which causes this to time out even when the page has actually loaded.
    # Waiting directly for the result card element is more reliable.

    # result cards follow the pattern data-test="search-flight-card-1", "-2", etc.
    page.wait_for_selector('[data-test^="search-flight-card-"]', timeout=30000)
    print("    Result cards appeared")
    cards = page.query_selector_all('[data-test^="search-flight-card-"]')

    results = []
    for card in cards:
        card_text = card.inner_text()

        price_match = re.search(r"PKR\s*([\d,]+)", card_text)
        if not price_match:
            continue
        price_value = float(price_match.group(1).replace(",", ""))

        airline_match = None
        for airline_name in KNOWN_AIRLINES:
            if airline_name.lower() in card_text.lower():
                airline_match = airline_name
                break

        results.append({
            "airline": airline_match or "Unknown",
            "price_pkr": price_value,
        })

    return results


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    travel_date = date.today() + timedelta(days=SEARCH_DAYS_AHEAD)
    today = date.today().isoformat()

    snapshot = {
        "scraped_date": today,
        "search_date": travel_date.isoformat(),
        "source": "https://www.sastaticket.pk",
        "routes": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for origin, destination, route_code in ROUTES:
            print(f"Scraping {route_code} ({origin} -> {destination})...")
            try:
                results = scrape_route(page, origin, destination, travel_date)
                snapshot["routes"][route_code] = results
                print(f"  Found {len(results)} fares")
            except PWTimeout:
                print(f"  Timed out — site structure may have changed, or route unavailable")
                snapshot["routes"][route_code] = []

        browser.close()

    out_path = RAW_DIR / f"competitor_prices_{today}.json"
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"Saved snapshot: {out_path}")


if __name__ == "__main__":
    main()