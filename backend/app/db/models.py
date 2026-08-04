import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    trips: Mapped[list["Trip"]] = relationship(back_populates="user")

class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    destination: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    budget: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="USD")
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    travelers: Mapped[int] = mapped_column(Integer, default=1)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True) # stores distances, cost breakdowns, maps routes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="trips")
    days: Mapped[list["Day"]] = relationship(back_populates="trip", cascade="all, delete-orphan")

class Day(Base):
    __tablename__ = "days"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"))
    day_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="days")
    items: Mapped[list["ItineraryItem"]] = relationship(back_populates="day", cascade="all, delete-orphan")

class ItineraryItem(Base):
    __tablename__ = "itinerary_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    day_id: Mapped[str] = mapped_column(ForeignKey("days.id"))
    order: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String)   # attraction | restaurant | activity | transport
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_mins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    place_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_level: Mapped[str | None] = mapped_column(String, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # New detailed columns
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entry_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_time_to_visit: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_from_prev: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_from_prev: Mapped[float | None] = mapped_column(Float, nullable=True)
    directions_link: Mapped[str | None] = mapped_column(String, nullable=True)
    google_maps_link: Mapped[str | None] = mapped_column(String, nullable=True)
    arrival_time: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String, nullable=True)

    day: Mapped["Day"] = relationship(back_populates="items")
