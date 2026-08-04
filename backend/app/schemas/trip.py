from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ItineraryItemBase(BaseModel):
    order: int
    type: str
    name: str
    description: Optional[str] = None
    start_time: Optional[str] = None
    duration_mins: Optional[int] = None
    estimated_cost: Optional[float] = None
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    rating: Optional[float] = None
    price_level: Optional[str] = None
    photo_url: Optional[str] = None
    address: Optional[str] = None
    
    # New detailed fields
    reviews_count: Optional[int] = None
    opening_hours: Optional[Dict[str, Any]] = None
    entry_fee: Optional[float] = None
    best_time_to_visit: Optional[str] = None
    category: Optional[str] = None
    distance_from_prev: Optional[float] = None
    duration_from_prev: Optional[float] = None
    directions_link: Optional[str] = None
    google_maps_link: Optional[str] = None
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None

class ItineraryItemResponse(ItineraryItemBase):
    id: str
    day_id: str

    model_config = {"from_attributes": True}

class DayBase(BaseModel):
    day_number: int
    title: Optional[str] = None

class DayResponse(DayBase):
    id: str
    trip_id: str
    items: List[ItineraryItemResponse] = []

    model_config = {"from_attributes": True}

class TripBase(BaseModel):
    destination: str
    budget: float
    currency: str = "USD"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: int = 1
    interests: List[str] = []

class TripCreate(TripBase):
    pass

class TripResponse(TripBase):
    id: str
    user_id: str
    lat: float
    lng: float
    summary: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    days: List[DayResponse] = []

    model_config = {"from_attributes": True}
