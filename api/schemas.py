"""Pydantic request/response models for the pricing API."""
from pydantic import BaseModel
from typing import Optional

class PriceRecommendationRequest(BaseModel):
    route: str
    flight_class: str
    days_to_departure: int
    total_seats: int
    remaining_seats: int

class PriceRecommendationResponse(BaseModel):
    route: str
    flight_class: str
    recommended_price: float
    expected_revenue: float
    predicted_demand_ratio: float
    candidates_evaluated: int
    competitor_data_is_real: bool

class DemandAtPriceRequest(BaseModel):
    route: str
    flight_class: str
    days_to_departure: int
    price: float

class DemandAtPriceResponse(BaseModel):
    route: str
    flight_class: str
    price: float
    predicted_demand_ratio: float

class PriceHistoryItem(BaseModel):
    route: str
    flight_class: str
    price: float
    expected_revenue: Optional[float]
    predicted_demand_ratio: Optional[float]
    trigger_reason: Optional[str]
    recorded_at: str

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    model_loaded: bool

class ETLTriggerResponse(BaseModel):
    status: str
    message: str
