# Dataset Preparation Script for PIA Dynamic Pricing Demand Model

"""
This script extracts historical flight records and external market signals from
Data_load/flight.db, performs feature engineering (including macro signals,
competitor pricing, holiday flags, booking date, time‑of‑day, day‑of‑week,
weekend indicator, base fare, etc.), and exports a clean dataset
(models/training_dataset.csv) ready for XGBoost model training.
"""

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Paths
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Data_load" / "flight.db"
MODELS_DIR = ROOT / "models"
OUTPUT_CSV = MODELS_DIR / "training_dataset.csv"


def load_raw_data(db_path: Path):
    """Load flights and external signals from the SQLite DB."""
    conn = sqlite3.connect(db_path)
    flights_df = pd.read_sql_query("SELECT * FROM flights", conn)
    signals_df = pd.read_sql_query("SELECT * FROM external_signals", conn)
    conn.close()
    return flights_df, signals_df


def get_latest_signal_val(signals_df: pd.DataFrame, signal_type: str, default: float) -> float:
    """Return the most recent value for a global signal, or a default if missing."""
    sub = signals_df[signals_df["signal_type"] == signal_type].sort_values("recorded_date", ascending=False)
    if not sub.empty:
        return float(sub.iloc[0]["value"])
    return default


def get_competitor_stats_by_route(signals_df: pd.DataFrame) -> dict:
    """Extract competitor min/avg price per route and class.
    Expected signal_type format: competitor_price_<class>
    """
    comp_df = signals_df[signals_df["signal_type"].str.startswith("competitor_price")].copy()
    route_stats = {}
    if not comp_df.empty:
        for (route, signal), group in comp_df.groupby(["route", "signal_type"]):
            cls_name = signal.split("_")[-1]
            stats = group["value"].agg(["min", "mean"]).to_dict()
            if route not in route_stats:
                route_stats[route] = {}
            route_stats[route][f"competitor_min_price_{cls_name}"] = stats["min"]
            route_stats[route][f"competitor_avg_price_{cls_name}"] = stats["mean"]
    return route_stats


def generate_time_varying_signal(base: float, days: np.ndarray) -> np.ndarray:
    """Random noise around the baseline macro signal (±10 units)."""
    noise = np.random.uniform(-10, 10, size=days.shape)
    return base + noise


def prepare_dataset():
    """ETL + feature engineering for the dynamic pricing MVP."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Connecting to DB at {DB_PATH}…")
    flights_df, signals_df = load_raw_data(DB_PATH)
    print(f"Loaded {len(flights_df)} flights and {len(signals_df)} external signals.")

    # 1️⃣ Global macro baselines (latest snapshot)
    base_petrol = get_latest_signal_val(signals_df, "petrol_price", default=335.18)
    base_diesel = get_latest_signal_val(signals_df, "diesel_price", default=383.46)
    base_usd = get_latest_signal_val(signals_df, "usd_to_pkr", default=277.86)
    print(f"Baseline macro -> Petrol:{base_petrol} Diesel:{base_diesel} USD/PKR:{base_usd}")

    # 2️⃣ Holiday dates (real calendar)
    holidays_df = signals_df[signals_df["signal_type"] == "holiday"].copy()
    holidays = set(pd.to_datetime(holidays_df["recorded_date"]).dt.date)

    # 3️⃣ Competitor stats per route & class
    competitor_stats = get_competitor_stats_by_route(signals_df)

    # 4️⃣ Feature engineering on flights
    df = flights_df.copy()
    df["demand_ratio"] = (df["booked_seats"] / df["total_seats"]).clip(0.0, 1.0)

    # Temporal features – fixed reference start date (2026‑07‑01)
    reference_date = pd.Timestamp('2026-07-01')
    df["departure_date"] = reference_date + pd.to_timedelta(df["days_to_departure"], unit='D')
    # Booking date = day before departure
    df["booking_date"] = df["departure_date"] - pd.to_timedelta(df["days_to_departure"], unit='D')
    df["time_of_day"] = (df["id"] % 24).astype(int)
    df["day_of_week"] = df["departure_date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_holiday_window"] = df["departure_date"].dt.date.apply(
        lambda d: int(any(abs((d - h).days) <= 2 for h in holidays))
    )

    # Base fare per route & class (mean of current_price)
    df["base_fare"] = df.groupby(["route", "flight_class"])["current_price"].transform('mean')

    # Macro signals varying with booking date offset
    min_booking = df["booking_date"].min()
    days_since_start = (df["booking_date"] - min_booking).dt.days.values
    df["petrol_price"] = generate_time_varying_signal(base_petrol, days_since_start)
    df["diesel_price"] = generate_time_varying_signal(base_diesel, days_since_start)
    df["usd_to_pkr"] = generate_time_varying_signal(base_usd, days_since_start)

    # Competitor pricing – real data only, NaN otherwise
    real_competitor_routes = {"KHI-LHE", "KHI-ISB"}
    df["competitor_min_price"] = np.nan
    df["competitor_avg_price"] = np.nan
    df["price_vs_competitor_ratio"] = np.nan
    df["competitor_data_is_real"] = False

    def comp_min(route, cls):
        key = f"competitor_min_price_{cls.lower()}"
        return competitor_stats.get(route, {}).get(key, np.nan)

    def comp_avg(route, cls):
        key = f"competitor_avg_price_{cls.lower()}"
        return competitor_stats.get(route, {}).get(key, np.nan)

    df["competitor_min_price"] = df.apply(lambda r: comp_min(r["route"], r["flight_class"]), axis=1)
    df["competitor_avg_price"] = df.apply(lambda r: comp_avg(r["route"], r["flight_class"]), axis=1)
    df["price_vs_competitor_ratio"] = df["current_price"] / df["competitor_avg_price"]
    df["competitor_data_is_real"] = df["route"].isin(real_competitor_routes)

    # Final column order (including the new flag)
    feature_columns = [
        "id",
        "route",
        "flight_class",
        "days_to_departure",
        "total_seats",
        "booked_seats",
        "remaining_seats",
        "current_price",
        "base_fare",
        "booking_date",
        "time_of_day",
        "day_of_week",
        "is_weekend",
        "is_holiday_window",
        "petrol_price",
        "diesel_price",
        "usd_to_pkr",
        "competitor_min_price",
        "competitor_avg_price",
        "price_vs_competitor_ratio",
        "competitor_data_is_real",
        "demand_ratio",
    ]

    final_df = df[feature_columns]
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Dataset generated - shape {final_df.shape} -> {OUTPUT_CSV}")
    return final_df


if __name__ == "__main__":
    prepare_dataset()
