"""
Streamlit dashboard for the PIA dynamic pricing MVP.
Calls the FastAPI backend only -- never touches the database directly.

Run the API first in a separate terminal:
    uv run uvicorn api.main:app --port 8000
Then run this dashboard:
    uv run streamlit run ui/app.py
"""
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

ROUTES = ["KHI-LHE", "KHI-ISB", "KHI-DXB", "LHE-ISB", "KHI-PEW"]
CLASSES = ["Economy", "Business"]

def get_json_response(resp):
    try:
        return resp.json()
    except ValueError:
        return None

def fetch_latest_prices():
    resp = requests.get(f"{API_BASE_URL}/pricing/history/latest", timeout=10)
    data = get_json_response(resp)
    if resp.status_code != 200:
        detail = data.get("detail") if isinstance(data, dict) else resp.text[:300]
        raise RuntimeError(detail or "Could not load latest price history.")
    return data or []

def render_latest_price_table():
    try:
        latest_prices = fetch_latest_prices()
    except Exception as e:
        st.warning(f"Could not load latest batch prices: {e}")
        return

    if not latest_prices:
        st.info("No batch repricing history yet.")
        return

    rows = []
    for item in latest_prices:
        rows.append({
            "Route": item["route"],
            "Class": item["flight_class"],
            "Recommended Price (PKR)": round(item["price"], 2),
            "Expected Revenue (PKR)": round(item["expected_revenue"], 2) if item["expected_revenue"] is not None else None,
            "Predicted Demand (%)": round(item["predicted_demand_ratio"] * 100, 2) if item["predicted_demand_ratio"] is not None else None,
            "Updated At": item["recorded_at"],
        })
    st.dataframe(rows, hide_index=True, width='stretch')

def fetch_signals_history():
    resp = requests.get(f"{API_BASE_URL}/signals/history", timeout=10)
    data = get_json_response(resp)
    if resp.status_code != 200:
        detail = data.get("detail") if isinstance(data, dict) else resp.text[:300]
        raise RuntimeError(detail or "Could not load market signals history.")
    return data or []

def render_signals_history_table():
    try:
        signals = fetch_signals_history()
    except Exception as e:
        st.warning(f"Could not load market signals: {e}")
        return

    if not signals:
        st.info("No market signals recorded yet.")
        return

    rows = []
    for item in signals:
        rows.append({
            "Signal Type": item.get("signal_type"),
            "Route": item.get("route") or "GLOBAL",
            "Value": item.get("value"),
            "Recorded Date": item.get("recorded_date"),
        })
    st.dataframe(rows, hide_index=True, width='stretch')

st.set_page_config(page_title="PIA Dynamic Pricing Cockpit", layout="wide")
st.title("PIA Dynamic Pricing (Revenue Management Cockpit)")

# --- Sidebar: API health check ---
with st.sidebar:
    st.header("System Status")
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=8).json()
        if health["status"] == "ok":
            st.success("API: Connected")
        else:
            st.warning("API: Degraded")
        st.write(f"Database: {'OK' if health['database_connected'] else 'Unavailable'}")
        st.write(f"Model loaded: {'OK' if health['model_loaded'] else 'Unavailable'}")
    except requests.exceptions.Timeout:
        st.warning("API Timeout: The local API is busy or loading the MLflow model...")
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach API. Is it running? (uv run uvicorn api.main:app --port 8000)")
        st.stop()

    st.divider()
    if st.button("Trigger Manual ETL Refresh"):
        with st.spinner("Running scrapers..."):
            try:
                resp = requests.post(f"{API_BASE_URL}/signals/trigger-etl", timeout=120).json()
                st.success(resp["message"])
            except Exception as e:
                st.error(f"ETL trigger failed: {e}")

tab1, tab2, tab3 = st.tabs(["Live Pricing", "Elasticity Simulator", "Market Signals"])

# --- Tab 1: Live Pricing Dashboard ---
with tab1:
    st.subheader("Get Price Recommendation")
    col1, col2, col3 = st.columns(3)
    with col1:
        route = st.selectbox("Route", ROUTES)
        flight_class = st.selectbox("Class", CLASSES)
    with col2:
        days_to_departure = st.slider("Days to Departure", 0, 90, 10)
        total_seats = st.number_input("Total Seats", value=180, min_value=1)
    with col3:
        remaining_seats = st.number_input("Remaining Seats", value=90, min_value=0, max_value=total_seats)

    if st.button("Get Recommended Price", type="primary"):
        with st.spinner("Optimizing price..."):
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/pricing/recommend",
                    json={
                        "route": route,
                        "flight_class": flight_class,
                        "days_to_departure": days_to_departure,
                        "total_seats": total_seats,
                        "remaining_seats": remaining_seats,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Recommended Price", f"{data['recommended_price']:,.0f} PKR")
                    m2.metric("Expected Revenue", f"{data['expected_revenue']:,.0f} PKR")
                    m3.metric("Predicted Demand", f"{data['predicted_demand_ratio'] * 100:.1f}%")
                    if data["competitor_data_is_real"]:
                        st.caption("Priced with real competitor data")
                    else:
                        st.caption("No real competitor data for this route -- price based on guardrails only")
                else:
                    st.error(resp.json().get("detail", "Unknown error"))
            except Exception as e:
                st.error(f"Request failed: {e}")

    st.divider()
    if st.button("Reprice ALL Routes (Batch)"):
        st.info("Repricing in progress... This may take a few minutes as it re-scrapes live competitor and fuel data.")
        with st.spinner("Running full repricing cycle..."):
            try:
                resp = requests.post(f"{API_BASE_URL}/pricing/batch-reprice", timeout=300)
                data = get_json_response(resp)
                if data is None:
                    st.error(f"Batch reprice failed: API returned non-JSON response ({resp.status_code}).")
                    st.code(resp.text[:1000] or "<empty response>")
                    st.stop()

                if resp.status_code == 200:
                    st.success(data["message"])
                    st.subheader("Latest Batch Recommended Prices")
                    render_latest_price_table()
                else:
                    st.error(data.get("detail", "Batch reprice failed."))
            except Exception as e:
                st.error(f"Batch reprice failed: {e}")

# --- Tab 2: Elasticity Simulator ---
with tab2:
    st.subheader("Price Elasticity Simulator")
    st.caption("See how predicted demand changes as price varies, for a fixed route/context.")
    sim_route = st.selectbox("Route", ROUTES, key="sim_route")
    sim_class = st.selectbox("Class", CLASSES, key="sim_class")
    sim_days = st.slider("Days to Departure", 0, 90, 10, key="sim_days")

    if st.button("Run Simulation"):
        prices = list(range(5000, 100000, 5000))
        demands = []
        with st.spinner("Simulating..."):
            for price in prices:
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/pricing/predict-demand-at-price",
                        json={
                            "route": sim_route,
                            "flight_class": sim_class,
                            "days_to_departure": sim_days,
                            "price": price,
                        },
                        timeout=30,
                    )
                    demands.append(resp.json().get("predicted_demand_ratio", None) if resp.status_code == 200 else None)
                except Exception:
                    demands.append(None)
        st.line_chart({"price": prices, "predicted_demand": demands}, x="price", y="predicted_demand")

# --- Tab 3: Market Signal Monitor ---
with tab3:
    st.subheader("Market Signals & Autopilot Log")
    st.caption("Recent market signal updates (fuel, FX, competitor prices) retrieved from local SQLite database.")
    render_signals_history_table()

