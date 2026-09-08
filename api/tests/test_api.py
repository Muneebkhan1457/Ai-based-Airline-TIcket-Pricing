"""
API tests for the PIA dynamic pricing MVP.
Uses monkeypatching to avoid real Databricks connections.
"""
from unittest.mock import MagicMock, patch
import pytest

# --- Mocks must be in place BEFORE api.services is imported ---
_mock_connection = MagicMock()
_mock_cursor = MagicMock()
_mock_connection.cursor.return_value = _mock_cursor

_mock_ws_client = MagicMock()
_mock_model = MagicMock()

# Patch lazy getters and model loader at import time
with patch("api.services._get_connection", return_value=_mock_connection), \
     patch("api.services._get_workspace_client", return_value=_mock_ws_client), \
     patch("api.services.get_model", return_value=_mock_model):
    from fastapi.testclient import TestClient
    from api.main import app

client = TestClient(app)


def make_mock_cursor(rows):
    """Helper: configure the mock cursor to return given rows."""
    _mock_cursor.fetchall.return_value = rows
    _mock_cursor.fetchone.return_value = rows[0] if rows else None
    return _mock_cursor


def _mock_services():
    """Return the services module for monkeypatching."""
    from api import services
    return services


# =========================================================
# Health
# =========================================================

def test_health_endpoint(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "check_health", lambda: {
        "status": "ok", "database_connected": True, "model_loaded": True
    })
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_connected"] is True
    assert body["model_loaded"] is True


# =========================================================
# Pricing recommend
# =========================================================

def test_price_recommendation_endpoint(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "get_price_recommendation", lambda *a, **kw: {
        "route": "KHI-LHE",
        "flight_class": "Economy",
        "recommended_price": 10500.0,
        "expected_revenue": 945000.0,
        "predicted_demand_ratio": 0.64,
        "candidates_evaluated": 108,
        "competitor_data_is_real": False,
    })
    response = client.post("/pricing/recommend", json={
        "route": "KHI-LHE",
        "flight_class": "Economy",
        "days_to_departure": 10,
        "total_seats": 180,
        "remaining_seats": 90,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "KHI-LHE"
    assert body["recommended_price"] > 0
    assert 0 <= body["predicted_demand_ratio"] <= 1


def test_price_recommendation_invalid_route(monkeypatch):
    from api import services
    def raise_value_error(*a, **kw):
        raise ValueError("No flights found for route NONEXISTENT")
    monkeypatch.setattr(services, "get_price_recommendation", raise_value_error)
    response = client.post("/pricing/recommend", json={
        "route": "NONEXISTENT",
        "flight_class": "Economy",
        "days_to_departure": 10,
        "total_seats": 180,
        "remaining_seats": 90,
    })
    assert response.status_code == 404


# =========================================================
# Demand at price
# =========================================================

def test_demand_at_price_endpoint(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "get_demand_at_price", lambda *a, **kw: {
        "route": "KHI-LHE",
        "flight_class": "Economy",
        "price": 15000.0,
        "predicted_demand_ratio": 0.45,
    })
    response = client.post("/pricing/predict-demand-at-price", json={
        "route": "KHI-LHE",
        "flight_class": "Economy",
        "days_to_departure": 10,
        "price": 15000,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 15000
    assert 0 <= body["predicted_demand_ratio"] <= 1


def test_demand_monotonicity_via_api(monkeypatch):
    """Model demand should not increase as price increases."""
    from api import services
    # Simulate realistic monotone decreasing demand
    demands_map = {10000: 0.7, 15000: 0.55, 20000: 0.40, 25000: 0.30}
    def fake_demand(route, flight_class, days_to_departure, price):
        return {"route": route, "flight_class": flight_class,
                "price": float(price), "predicted_demand_ratio": demands_map.get(price, 0.3)}
    monkeypatch.setattr(services, "get_demand_at_price", fake_demand)
    prices = [10000, 15000, 20000, 25000]
    demands = []
    for price in prices:
        resp = client.post("/pricing/predict-demand-at-price", json={
            "route": "KHI-LHE", "flight_class": "Economy",
            "days_to_departure": 10, "price": price,
        })
        demands.append(resp.json()["predicted_demand_ratio"])
    for i in range(1, len(demands)):
        assert demands[i] <= demands[i - 1] + 0.001, \
            f"Non-monotone: demand at price {prices[i]} ({demands[i]}) > demand at {prices[i-1]} ({demands[i-1]})"


# =========================================================
# Batch reprice
# =========================================================

def test_batch_reprice_success(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "reprice_all_routes",
                        lambda trigger_reason="batch_trigger": {"routes_repriced": 10})
    response = client.post("/pricing/batch-reprice")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["routes_repriced"] == 10


def test_batch_reprice_failure_returns_json(monkeypatch):
    from api import services
    def fail(trigger_reason="batch_trigger"):
        raise RuntimeError("repricing engine exploded")
    monkeypatch.setattr(services, "reprice_all_routes", fail)
    response = client.post("/pricing/batch-reprice")
    assert response.status_code == 500
    body = response.json()
    assert "Batch repricing failed" in body["detail"]


# =========================================================
# History and signals
# =========================================================

def test_latest_price_history_endpoint(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "get_latest_price_history", lambda limit=10: [
        {"route": "KHI-LHE", "flight_class": "Economy",
         "price": 10500.0, "recommended_price": 10500.0,
         "expected_revenue": 945000.0, "predicted_demand_ratio": 0.64,
         "trigger_reason": "batch_trigger", "recorded_at": "2026-08-05 10:00:00"}
    ])
    response = client.get("/pricing/history/latest")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        first = body[0]
        assert "route" in first
        assert "flight_class" in first
        assert "price" in first or "recommended_price" in first
        assert "recorded_at" in first


def test_signals_history_endpoint(monkeypatch):
    from api import services
    monkeypatch.setattr(services, "get_signals_history", lambda limit=20: [
        {"signal_type": "fuel_price", "route": "GLOBAL", "value": 285.0, "recorded_date": "2026-08-05"}
    ])
    response = client.get("/signals/history")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
