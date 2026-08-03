"""FastAPI app for the PIA dynamic pricing MVP. Run: uv run uvicorn api.main:app --reload"""
from fastapi import FastAPI, HTTPException

from api.schemas import (
    PriceRecommendationRequest, PriceRecommendationResponse,
    DemandAtPriceRequest, DemandAtPriceResponse,
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
    from scheduler.run_autopilot import scheduled_check
    scheduled_check()
    return {"status": "ok", "message": "Batch repricing cycle completed. Check price_history table."}

@app.post("/signals/trigger-etl", response_model=ETLTriggerResponse)
def trigger_etl():
    from scheduler.jobs import run_fuel_job, run_competitor_job, run_fx_job
    try:
        run_fuel_job()
        run_competitor_job()
        run_fx_job()
        return {"status": "ok", "message": "All scrapers and ETL jobs completed."}
    except Exception as e:
        return {"status": "partial_failure", "message": str(e)}
