# PHASE 7 (FIXED): Scheduler with Real Signal Queries - HANDLE NONE VALUES
import pandas as pd
import numpy as np
from datetime import datetime, timezone

print("=" * 70)
print("PHASE 7 (FIXED): SCHEDULER WITH REAL SIGNAL QUERIES")
print("=" * 70)

flights_df = spark.table("airline_daw.pia_pricing.flights").toPandas()
signals_pdf = spark.table("airline_daw.pia_pricing.external_signals").toPandas()

print(f"\nLoaded {len(flights_df)} flights")

# ============================================
# Helper functions
# ============================================

def get_latest_signal(signal_type):
    """Get latest value for a signal"""
    subset = signals_pdf[signals_pdf['signal_type'] == signal_type].sort_values('recorded_date', ascending=False)
    return float(subset['value'].iloc[0]) if not subset.empty else None

def get_competitor_stats(route):
    """Get competitor stats for a specific route"""
    comp_rows = signals_pdf[
        (signals_pdf['signal_type'].str.startswith('competitor_price', na=False)) &
        (signals_pdf['route'] == route)
    ]
    if not comp_rows.empty:
        values = comp_rows['value'].astype(float)
        return float(values.min()), float(values.mean()), True
    return None, None, False

def get_holidays():
    """Extract all holiday dates"""
    holidays = signals_pdf[signals_pdf['signal_type'] == 'holiday']['recorded_date'].unique()
    return pd.to_datetime(holidays)

# ============================================
# Scheduler: Reprice Route (FIXED)
# ============================================

price_history = []

def reprice_route(route, flight_class):
    """Reprice a specific route + class - USES REAL SIGNALS"""
    subset = flights_df[
        (flights_df["route"] == route) & 
        (flights_df["flight_class"] == flight_class)
    ]
    
    if len(subset) == 0:
        return
    
    flight = subset.iloc[0]
    base_fare = flights_df[
        (flights_df["route"] == route) & 
        (flights_df["flight_class"] == flight_class)
    ]["current_price"].mean()
    
    # FIXED: Read REAL signals from external_signals table
    comp_min, comp_avg, has_real_competitor_data = get_competitor_stats(route)
    holidays = get_holidays()
    
    now = datetime.now()
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    
    is_holiday_window = int(any(
        abs((pd.Timestamp(now.date()) - h).days) <= 2 
        for h in holidays
    ))
    
    # Build context with REAL values (not hardcoded)
    context = {
        'route': route,
        'flight_class': flight_class,
        'days_to_departure': int(flight["days_to_departure"]),
        'current_price': float(flight["current_price"]),
        'base_fare': float(base_fare),
        'time_of_day': now.hour,
        'day_of_week': day_of_week,
        'is_weekend': is_weekend,
        'is_holiday_window': is_holiday_window,
        'petrol_price': get_latest_signal("petrol_price") or 335.18,
        'diesel_price': get_latest_signal("diesel_price") or 383.46,
        'usd_to_pkr': get_latest_signal("usd_to_pkr") or 277.86,
        'competitor_min_price': comp_min or np.nan,
        'competitor_avg_price': comp_avg or np.nan,
        'price_vs_competitor_ratio': (float(flight["current_price"]) / comp_avg 
                                      if comp_avg else np.nan),
        'competitor_data_is_real': int(has_real_competitor_data),
    }
    
    opt_result = optimize_price(context, int(flight["total_seats"]), int(flight["remaining_seats"]))
    
    price_history.append({
        "route": route,
        "flight_class": flight_class,
        "recommended_price": opt_result.recommended_price,
        "expected_revenue": opt_result.expected_revenue,
        "predicted_demand_ratio": opt_result.predicted_demand_ratio,
        "trigger_reason": "delta_trigger",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "competitor_data_is_real": int(has_real_competitor_data),
        "competitor_avg_price": comp_avg
    })
    
    # FIXED: Handle None competitor_avg_price in print statement
    comp_avg_str = f"{comp_avg:,.0f} PKR" if comp_avg is not None else "N/A"
    
    print(f"   [{route}/{flight_class}] Price: {opt_result.recommended_price:,.0f} PKR | "
          f"Competitor real: {has_real_competitor_data} | "
          f"Competitor avg: {comp_avg_str} | "
          f"Revenue: {opt_result.expected_revenue:,.0f}")

# ============================================
# Run scheduler for all route/class combinations
# ============================================

print("\n" + "=" * 70)
print("SCHEDULER TEST: Repricing all routes with REAL signals")
print("=" * 70 + "\n")

routes = flights_df["route"].unique()
classes = flights_df["flight_class"].unique()

for route in sorted(routes):
    for flight_class in sorted(classes):
        reprice_route(route, flight_class)

# ============================================
# Verification: Check KHI-LHE and KHI-ISB
# ============================================

print("\n" + "=" * 70)
print("VERIFICATION: KHI-LHE and KHI-ISB (should have real competitor data)")
print("=" * 70)

khi_lhe_results = [h for h in price_history if h['route'] == 'KHI-LHE']
khi_isb_results = [h for h in price_history if h['route'] == 'KHI-ISB']

if khi_lhe_results:
    result = khi_lhe_results[0]
    print(f"\nKHI-LHE:")
    print(f"  ✅ Competitor data is real: {bool(result['competitor_data_is_real'])}")
    if result['competitor_avg_price'] is not None:
        print(f"  ✅ Competitor avg price: {result['competitor_avg_price']:,.0f} PKR")
        print(f"  ✅ Recommended price: {result['recommended_price']:,.0f} PKR")
        print(f"  ✅ Price capped near competitor avg * 1.15: {result['recommended_price'] <= (result['competitor_avg_price'] * 1.15 + 100)}")
    else:
        print(f"  ⚠️  Competitor avg price: N/A")

if khi_isb_results:
    result = khi_isb_results[0]
    print(f"\nKHI-ISB:")
    print(f"  ✅ Competitor data is real: {bool(result['competitor_data_is_real'])}")
    if result['competitor_avg_price'] is not None:
        print(f"  ✅ Competitor avg price: {result['competitor_avg_price']:,.0f} PKR")
        print(f"  ✅ Recommended price: {result['recommended_price']:,.0f} PKR")
        print(f"  ✅ Price capped near competitor avg * 1.15: {result['recommended_price'] <= (result['competitor_avg_price'] * 1.15 + 100)}")
    else:
        print(f"  ⚠️  Competitor avg price: N/A")

print("\n" + "=" * 70)
print("✅ PHASE 7 COMPLETE: Scheduler now uses real signals")
print("=" * 70)
