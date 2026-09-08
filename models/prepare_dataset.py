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
    """Extract competitor min/avg price per route (all classes pooled).
    DB stores signal_type as competitor_price_1, competitor_price_2, etc.
    We aggregate all of them per route into a single min and mean.
    """
    comp_df = signals_df[signals_df["signal_type"].str.startswith("competitor_price")].copy()
    route_stats = {}
    if not comp_df.empty:
        for route, group in comp_df.groupby("route"):
            route_stats[route] = {
                "competitor_min_price": group["value"].min(),
                "competitor_avg_price": group["value"].mean(),
            }
    return route_stats


def generate_time_varying_signal(base: float, count: int) -> np.ndarray:
    """Random noise around the baseline macro signal (±10 units)."""
    noise = np.random.uniform(-10, 10, size=count)
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

    # Random per-row noise around the baseline macro signal — NOT tied to
    # any real date, since we only have one real snapshot per signal
    row_count = len(df)
    df["petrol_price"] = generate_time_varying_signal(base_petrol, row_count)
    df["diesel_price"] = generate_time_varying_signal(base_diesel, row_count)
    df["usd_to_pkr"] = generate_time_varying_signal(base_usd, row_count)

    # Competitor pricing – real data only, NaN otherwise
    real_competitor_routes = {"KHI-LHE", "KHI-ISB"}
    df["competitor_min_price"] = np.nan
    df["competitor_avg_price"] = np.nan
    df["price_vs_competitor_ratio"] = np.nan
    df["competitor_data_is_real"] = False

    def comp_min(route):
        return competitor_stats.get(route, {}).get("competitor_min_price", np.nan)

    def comp_avg(route):
        return competitor_stats.get(route, {}).get("competitor_avg_price", np.nan)

    df["competitor_min_price"] = df["route"].apply(comp_min)
    df["competitor_avg_price"] = df["route"].apply(comp_avg)
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
    
    # 📊 DISPLAY METRICS
    print("\n" + "="*60)
    print("✅ DATASET METRICS")
    print("="*60)
    print(f"\nShape: {final_df.shape[0]} flights × {final_df.shape[1]} features")
    print(f"\nFeatures:")
    for i, col in enumerate(feature_columns, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\n📈 DEMAND RATIO STATISTICS:")
    print(final_df["demand_ratio"].describe())
    
    print(f"\n🎯 KEY STATISTICS:")
    print(f"  Average occupancy: {final_df['demand_ratio'].mean():.2%}")
    print(f"  Min occupancy: {final_df['demand_ratio'].min():.2%}")
    print(f"  Max occupancy: {final_df['demand_ratio'].max():.2%}")
    print(f"  Std deviation: {final_df['demand_ratio'].std():.4f}")
    
    print(f"\n💰 PRICE STATISTICS:")
    print(f"  Average price: {final_df['current_price'].mean():,.0f} PKR")
    print(f"  Min price: {final_df['current_price'].min():,.0f} PKR")
    print(f"  Max price: {final_df['current_price'].max():,.0f} PKR")
    
    print(f"\n⛽ EXTERNAL SIGNALS:")
    print(f"  Petrol (avg): {final_df['petrol_price'].mean():.2f} PKR/L")
    print(f"  Diesel (avg): {final_df['diesel_price'].mean():.2f} PKR/L")
    print(f"  USD/PKR (avg): {final_df['usd_to_pkr'].mean():.2f}")
    
    print(f"\n🎯 COMPETITOR DATA:")
    print(f"  Routes with real competitor data: {final_df['competitor_data_is_real'].sum()} flights")
    print(f"  Avg competitor price: {final_df['competitor_avg_price'].mean():,.0f} PKR")
    
    print(f"\n📅 TEMPORAL FEATURES:")
    print(f"  Weekend flights: {final_df['is_weekend'].sum()} ({final_df['is_weekend'].mean():.1%})")
    print(f"  Holiday window flights: {final_df['is_holiday_window'].sum()} ({final_df['is_holiday_window'].mean():.1%})")
    
    print("\n" + "="*60)
    print("✅✅✅ FEATURE ENGINEERING COMPLETE ✅✅✅")
    print("="*60 + "\n")
    
    return final_df


if __name__ == "__main__":
    prepare_dataset()
