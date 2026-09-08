"""FastAPI app for the PIA dynamic pricing MVP. Run: uv run uvicorn api.main:app --reload"""
from typing import List

from fastapi import FastAPI, HTTPException

from api.schemas import (
    PriceRecommendationRequest, PriceRecommendationResponse,
    DemandAtPriceRequest, DemandAtPriceResponse,
    PriceHistoryItem,
    HealthResponse, ETLTriggerResponse
)
from api import services

app = FastAPI(title="PIA Dynamic Pricing API", version="0.1.0")

@app.get("/health", response_model=HealthResponse)
def health():
    return services.check_health()

@app.post("/pricing/recommend", response_model=PriceRecommendationResponse)
def recommend_price(req: PriceRecommendationRequest):
    try:
        return services.get_price_recommendation(
            req.route, req.flight_class, req.days_to_departure,
            req.total_seats, req.remaining_seats
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/pricing/predict-demand-at-price", response_model=DemandAtPriceResponse)
def predict_demand_at_price_endpoint(req: DemandAtPriceRequest):
    try:
        return services.get_demand_at_price(
            req.route, req.flight_class, req.days_to_departure, req.price
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/pricing/batch-reprice")
def batch_reprice():
    try:
        result = services.reprice_all_routes(trigger_reason="batch_trigger")
        message = f"Batch repricing completed: {result['routes_repriced']} route/class combinations priced."
        return {"status": "ok", "message": message, "routes_repriced": result["routes_repriced"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch repricing failed: {e}")

@app.get("/pricing/history/latest", response_model=List[PriceHistoryItem])
def latest_price_history(limit: int = 10):
    return services.get_latest_price_history(limit=limit)

@app.get("/signals/history")
def signals_history(limit: int = 20):
    return services.get_signals_history(limit=limit)

@app.post("/signals/trigger-etl", response_model=ETLTriggerResponse)
def trigger_etl():
    from scheduler.databricks_autopilot import run_etl_and_push
    try:
        pushed = run_etl_and_push()
        return {"status": "ok", "message": f"All scrapers and ETL jobs completed. Signals pushed to Databricks: {pushed}."}
    except Exception as e:
        return {"status": "partial_failure", "message": str(e)}

