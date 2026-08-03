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

st.set_page_config(page_title="PIA Dynamic Pricing Cockpit", layout="wide")
st.title("PIA Dynamic Pricing -- Revenue Management Cockpit")

# --- Sidebar: API health check ---
with st.sidebar:
    st.header("System Status")
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5).json()
        if health["status"] == "ok":
            st.success("API: Connected")
        else:
            st.warning("API: Degraded")
        st.write(f"Database: {'OK' if health['database_connected'] else 'Unavailable'}")
        st.write(f"Model loaded: {'OK' if health['model_loaded'] else 'Unavailable'}")
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
        with st.spinner("Running full repricing cycle..."):
            try:
                resp = requests.post(f"{API_BASE_URL}/pricing/batch-reprice", timeout=180).json()
                st.success(resp["message"])
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
            for _price in prices:
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/pricing/recommend",
                        json={
                            "route": sim_route,
                            "flight_class": sim_class,
                            "days_to_departure": sim_days,
                            "total_seats": 180,
                            "remaining_seats": 90,
                        },
                        timeout=30,
                    )
                    demands.append(resp.json().get("predicted_demand_ratio", None) if resp.status_code == 200 else None)
                except Exception:
                    demands.append(None)
        st.line_chart({"price": prices, "predicted_demand": demands}, x="price", y="predicted_demand")
        st.caption(
            "Note: this calls /pricing/recommend repeatedly, which re-optimizes each time rather than holding price "
            "fixed -- a true elasticity curve would need a dedicated /pricing/predict-demand-at-price endpoint. "
            "Flag this as a possible future improvement."
        )

# --- Tab 3: Market Signal Monitor ---
with tab3:
    st.subheader("Market Signals & Autopilot Log")
    st.caption(
        "This tab would show live fuel/competitor/FX trends and the price_history log. "
        "Since there's no dedicated API endpoint yet for querying price_history or raw signal trends, "
        "this is a placeholder -- a future GET /signals/history and GET /pricing/history endpoint "
        "would be needed to populate this properly instead of querying the DB directly from here."
    )
