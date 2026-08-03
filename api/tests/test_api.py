from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["database_connected"] is True
    assert body["model_loaded"] is True

def test_price_recommendation_endpoint():
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

def test_price_recommendation_invalid_route():
    response = client.post("/pricing/recommend", json={
        "route": "NONEXISTENT",
        "flight_class": "Economy",
        "days_to_departure": 10,
        "total_seats": 180,
        "remaining_seats": 90,
    })
    assert response.status_code == 404

def test_demand_at_price_endpoint():
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

def test_demand_monotonicity_via_api():
    """Confirms the API-exposed model is still monotonic: demand should not increase as price increases."""
    prices = [10000, 15000, 20000, 25000]
    demands = []
    for price in prices:
        response = client.post("/pricing/predict-demand-at-price", json={
            "route": "KHI-LHE",
            "flight_class": "Economy",
            "days_to_departure": 10,
            "price": price,
        })
        demands.append(response.json()["predicted_demand_ratio"])
    for index in range(1, len(demands)):
        assert demands[index] <= demands[index - 1] + 0.001
