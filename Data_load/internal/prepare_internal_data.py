"""
Internal data preparation script for the PIA dynamic pricing MVP.

Downloads a real Kaggle flight-price dataset (India domestic routes,
economy + business class), then transforms it into a PIA-style dataset:
  - loads both economy.csv and business.csv, tagging flight_class from filename
  - maps the real routes onto PIA-style routes
  - since this dataset has no days_left column, generates a synthetic
    but realistic days_to_departure per row
  - rescales price into a PKR-like range, using the real price's relative
    position within its class (so business fares stay proportionally
    higher than economy, as in the real data) rather than a flat re-roll

Output: internal/generated/flights_internal.csv

Requires: pip install kagglehub pandas --break-system-packages
Requires a Kaggle account + API token (kaggle.json) for kagglehub to
authenticate. See: https://www.kaggle.com/docs/api
"""

import random
from pathlib import Path

import kagglehub
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent / "generated"
OUTPUT_FILE = OUTPUT_DIR / "flights_internal.csv"

PIA_ROUTES = [
    ("Karachi", "Lahore", "KHI-LHE"),
    ("Karachi", "Islamabad", "KHI-ISB"),
    ("Karachi", "Dubai", "KHI-DXB"),
    ("Lahore", "Islamabad", "LHE-ISB"),
    ("Karachi", "Peshawar", "KHI-PEW"),
]

DOMESTIC_PRICE_RANGE_PKR = {
    "Economy": (8000, 22000),
    "Business": (25000, 60000),
}
INTERNATIONAL_PRICE_RANGE_PKR = {
    "Economy": (35000, 55000),
    "Business": (70000, 150000),
}


def download_dataset() -> Path:
    path = kagglehub.dataset_download("shubhambathwal/flight-price-prediction")
    print(f"Kaggle dataset downloaded to: {path}")
    return Path(path)


def load_raw_dataset(dataset_dir: Path) -> pd.DataFrame:
    """
    Loads every CSV in the dataset folder (typically economy.csv and
    business.csv), tagging each row's flight_class from the filename,
    since the files themselves don't contain a class column.
    """
    all_csv_files = list(dataset_dir.rglob("*.csv"))
    if not all_csv_files:
        raise FileNotFoundError(f"No CSV file found in {dataset_dir}")

    # Skip combined/summary files like "Clean_Dataset.csv" which overlap
    # with the separate economy.csv / business.csv files and would
    # otherwise duplicate the data.
    csv_files = [f for f in all_csv_files if "clean" not in f.stem.lower()]

    frames = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        inferred_class = "Business" if "business" in csv_file.stem.lower() else "Economy"
        df["flight_class"] = inferred_class

        # price sometimes arrives as a string with commas (e.g. "5,000")
        # and sometimes as a plain number - normalize both to float.
        df["price"] = pd.to_numeric(
            df["price"].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )
        df = df.dropna(subset=["price"])

        frames.append(df)
        print(f"Loaded {len(df)} rows from {csv_file.name} as {inferred_class}")

    combined = pd.concat(frames, ignore_index=True)
    print(f"Total combined rows: {len(combined)}")
    return combined


def rescale_price(original_price: float, price_percentile: float,
                   flight_class: str, is_international: bool) -> float:
    """
    Maps the original (INR) price's relative position within its own
    class distribution (0.0-1.0 percentile) onto a PKR-scale band, so
    the real data's spread and business-vs-economy gap is preserved.
    """
    ranges = INTERNATIONAL_PRICE_RANGE_PKR if is_international else DOMESTIC_PRICE_RANGE_PKR
    low, high = ranges[flight_class]
    base = low + (high - low) * price_percentile
    noise = random.uniform(-0.04, 0.04) * base
    return round(base + noise, 2)


def transform_to_pia_style(df: pd.DataFrame) -> pd.DataFrame:
    if "price" not in df.columns:
        raise KeyError(
            f"Expected a 'price' column, found columns: {list(df.columns)}. "
            "Inspect the dataset and adjust column names in this function."
        )

    # percentile rank of each row's price within its own class,
    # used to preserve relative price spread when rescaling to PKR
    df = df.copy()
    df["price_percentile"] = df.groupby("flight_class")["price"].rank(pct=True)

    rows = []
    for _, record in df.iterrows():
        origin, destination, route_code = random.choice(PIA_ROUTES)
        is_international = destination == "Dubai"
        flight_class = record["flight_class"]

        # dataset has no days_left column, so we generate a realistic
        # synthetic value: skewed toward closer-to-departure bookings,
        # matching typical real-world booking curves
        days_to_departure = int(random.triangular(0, 90, 5))

        rows.append(
            {
                "route": route_code,
                "origin": origin,
                "destination": destination,
                "days_to_departure": days_to_departure,
                "flight_class": flight_class,
                "price_pkr": rescale_price(
                    record["price"], record["price_percentile"],
                    flight_class, is_international,
                ),
                "total_seats": 180,
                # Blend a price-based signal with independent randomness so
                # demand is less deterministically tied to price.
                "booked_seats": int(
                    max(20,
                        min(175,
                            (
                                0.5 * (1 - record["price_percentile"]) +
                                0.5 * random.random()
                            ) * 180
                        )
                    )
                ),
            }
        )

    result = pd.DataFrame(rows)
    result["remaining_seats"] = result["total_seats"] - result["booked_seats"]
    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset_dir = download_dataset()
    raw_df = load_raw_dataset(dataset_dir)
    pia_df = transform_to_pia_style(raw_df)

    pia_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(pia_df)} PIA-style internal records to {OUTPUT_FILE}")
    print(pia_df.head())


if __name__ == "__main__":
    main()