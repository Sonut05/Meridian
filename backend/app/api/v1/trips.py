from fastapi import APIRouter, BackgroundTasks
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep, CurrentUser
from app.schemas.trip import TripCreate, TripResponse
from app.db.models import Trip, Day, ItineraryItem
from app.services.trip_service import create_trip

router = APIRouter()

@router.post("/", response_model=TripResponse)
async def create_new_trip(trip_in: TripCreate, current_user: CurrentUser, session: SessionDep, background_tasks: BackgroundTasks):
    """Create a new trip. Itinerary is generated synchronously for now."""
    trip = await create_trip(session=session, user_id=current_user.id, trip_in=trip_in)
    
    # To return full nested response, reload with selectinload
    stmt = (
        select(Trip)
        .options(selectinload(Trip.days).selectinload(Day.items))
        .where(Trip.id == trip.id)
    )
    result = await session.execute(stmt)
    full_trip = result.scalar_one()
    return full_trip

@router.get("/", response_model=List[TripResponse])
async def read_trips(current_user: CurrentUser, session: SessionDep):
    stmt = (
        select(Trip)
        .options(selectinload(Trip.days).selectinload(Day.items))
        .where(Trip.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/photo")
async def get_photo_proxy(photo_name: str):
    """Proxies the request to get a fresh redirect link for a Google Maps photo."""
    if not photo_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="photo_name is required")
    
    import httpx
    from app.services.google_maps import resolve_photo_url
    from fastapi.responses import RedirectResponse
    
    async with httpx.AsyncClient() as client:
        photo_url = await resolve_photo_url(client, photo_name)
        if photo_url:
            return RedirectResponse(url=photo_url)
            
    # Fallback to category placeholder if resolving photo fails
    return RedirectResponse(url="https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&auto=format&fit=crop&q=60")

@router.get("/{trip_id}", response_model=TripResponse)
async def read_trip(trip_id: str, current_user: CurrentUser, session: SessionDep):
    stmt = (
        select(Trip)
        .options(selectinload(Trip.days).selectinload(Day.items))
        .where(Trip.id == trip_id)
        .where(Trip.user_id == current_user.id)
    )
    result = await session.execute(stmt)
    trip = result.scalar_one_or_none()
    if not trip:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip
