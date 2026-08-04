from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Trip, Day, ItineraryItem
from app.schemas.trip import TripCreate
from app.services.google_maps import get_coordinates, search_popular_places, fetch_place_details
from app.services.optimizer import optimize_route, haversine_distance
from app.services.openai_agent import generate_itinerary
from app.services.cache_service import get_cache, set_cache
import urllib.parse
import asyncio
import httpx

async def fetch_wikipedia_image(query: str) -> str | None:
    """Fetches a real place photo from Wikipedia by search query, or returns None if not found."""
    q_clean = query.replace(" - Day ", " ").strip()
    cache_key = f"wiki_photo:{q_clean.lower()}"
    cached = await get_cache(cache_key)
    if cached and isinstance(cached, dict) and "url" in cached:
        return cached["url"]

    headers = {"User-Agent": "MeridianTripPlanner/1.0 (sonu@example.com)"}
    async with httpx.AsyncClient() as client:
        try:
            # 1. Search Wikipedia for matching page title
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q_clean)}&format=json"
            search_resp = await client.get(search_url, headers=headers, timeout=5.0)
            if search_resp.status_code == 200:
                data = search_resp.json()
                search_results = data.get("query", {}).get("search", [])
                if search_results:
                    title = search_results[0].get("title")
                    if title:
                        # 2. Fetch page image source URL
                        img_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles={urllib.parse.quote(title)}"
                        img_resp = await client.get(img_url, headers=headers, timeout=5.0)
                        if img_resp.status_code == 200:
                            img_data = img_resp.json()
                            pages = img_data.get("query", {}).get("pages", {})
                            for page_id, page_val in pages.items():
                                original = page_val.get("original", {})
                                source = original.get("source")
                                if source:
                                    clean_source = source.split("?")[0]
                                    await set_cache(cache_key, {"url": clean_source})
                                    return clean_source
        except Exception as e:
            print(f"Error fetching Wikipedia image for '{query}': {e}")
    return None

async def create_trip(session: AsyncSession, user_id: str, trip_in: TripCreate) -> Trip:
    # 1. Get destination coordinates
    lat, lng = await get_coordinates(trip_in.destination)
    
    # Calculate num days (default 3 if not specified)
    num_days = 3
    if trip_in.start_date and trip_in.end_date:
        delta = trip_in.end_date - trip_in.start_date
        num_days = max(1, delta.days + 1)
        
    # 2. Fetch popular places matching destination & interests
    places = await search_popular_places(trip_in.destination, trip_in.interests)
    
    # If no places found, create basic dummy places to feed the optimizer/generator
    if not places:
        places = [
            {"place_id": "dummy_1", "name": f"Central Park {trip_in.destination}", "lat": lat + 0.01, "lng": lng + 0.01, "rating": 4.5, "reviews_count": 120, "types": ["park"], "opening_hours": [], "address": "Center city"},
            {"place_id": "dummy_2", "name": f"Historic Temple of {trip_in.destination}", "lat": lat - 0.015, "lng": lng + 0.02, "rating": 4.8, "reviews_count": 340, "types": ["shrine"], "opening_hours": [], "address": "Old town"},
            {"place_id": "dummy_3", "name": f"City Museum of {trip_in.destination}", "lat": lat + 0.02, "lng": lng - 0.01, "rating": 4.2, "reviews_count": 85, "types": ["museum"], "opening_hours": [], "address": "Arts district"}
        ]
        
    # 3. Optimize route order using Traveling Salesperson (TSP) Nearest-Neighbor
    optimized_places = optimize_route(places)
    
    # 4. Ask OpenAI LLaMA to build a strict daily schedule using only these places
    itinerary_data = await generate_itinerary(
        destination=trip_in.destination,
        num_days=num_days,
        budget=trip_in.budget,
        currency=trip_in.currency,
        travelers=trip_in.travelers,
        interests=trip_in.interests,
        places=optimized_places
    )
    
    # Create lookup map of candidate places to retrieve coordinates and metadata later
    places_lookup = {p["place_id"]: p for p in optimized_places}
    places_name_lookup = {p["name"].lower(): p for p in optimized_places}
    
    # Pre-parse and resolve all items concurrently to avoid blocking network calls
    all_items_to_resolve = []
    for day_data in itinerary_data.get("days", []):
        for item_data in day_data.get("items", []):
            all_items_to_resolve.append(item_data)
            
    resolved_places = {}
    
    async def resolve_item_place(item_data):
        place_id = item_data.get("place_id")
        name = item_data.get("name", "")
        name_key = name.lower()
        
        # 1. Exact place_id match
        if place_id and place_id in places_lookup:
            return places_lookup[place_id]
            
        # 2. Exact name match
        if name_key in places_name_lookup:
            return places_name_lookup[name_key]
            
        # 3. Fuzzy name match against pre-fetched list
        for p in optimized_places:
            p_name_lower = p["name"].lower()
            if p_name_lower in name_key or name_key in p_name_lower:
                return p
                
        # 4. Query Google Maps search on the fly (for photos and lat/lng)
        on_the_fly = await fetch_place_details(name, trip_in.destination)
        if on_the_fly:
            return on_the_fly
            
        return None

    # Resolve all items concurrently
    resolve_tasks = [resolve_item_place(item) for item in all_items_to_resolve]
    resolved_results = await asyncio.gather(*resolve_tasks)
    
    # Map them back by name key
    for item, real_place in zip(all_items_to_resolve, resolved_results):
        if real_place:
            resolved_places[item.get("name", "").lower()] = real_place

    # Compute travel details and collect all coordinates in order for complete route URL
    ordered_coords = []
    total_distance_km = 0.0
    total_duration_mins = 0.0
    
    # Pre-parse days and items to enrich them
    parsed_days = []
    prev_item = None
    
    for day_data in itinerary_data.get("days", []):
        day_items = []
        for idx, item_data in enumerate(day_data.get("items", [])):
            name_key = item_data.get("name", "").lower()
            real_place = resolved_places.get(name_key)
            
            place_id = real_place["place_id"] if real_place else item_data.get("place_id")
            
            # Populate coords & ratings
            item_lat = real_place["lat"] if real_place else None
            item_lng = real_place["lng"] if real_place else None
            item_rating = real_place["rating"] if real_place else None
            item_reviews = real_place["reviews_count"] if real_place else 0
            item_hours = real_place["opening_hours"] if real_place else None
            item_addr = real_place["address"] if real_place else None
            
            cat = item_data.get("category", "General")
            
            # Use Google Maps place photo if available
            photo_url = None
            if real_place and real_place.get("photo_url"):
                photo_url = real_place["photo_url"]
            
            # If no photo on Google Maps, try fetching a real place photo from Wikipedia (only if name is not generic/offline fallback template)
            if not photo_url:
                name_clean = item_data.get("name")
                if name_clean:
                    name_lower = name_clean.lower()
                    generic_keywords = [
                        "traditional", "popular", "cozy", "famous", "authentic", "riverside", 
                        "gourmet", "classic", "premium", "local", "scenic", "historic", "eatery",
                        "bistro", "diner", "grill", "steakhouse", "culinary", "plaza", "landmark",
                        "wonder", "district", "village", "grounds", "trail", "spot", "place",
                        "restaurant", "cafe", "café", "bar", "pub", "food", "market", "shop",
                        "sight", "park", "garden", "walk", "stroll", "viewpoint"
                    ]
                    # If it's a real place name and doesn't contain generic offline template words, query Wikipedia
                    if "dummy" not in item_data.get("place_id", "") and not any(kw in name_lower for kw in generic_keywords):
                        photo_url = await fetch_wikipedia_image(name_clean)
            
            # Fallback to category/place-related Unsplash image if no google map/wiki photo
            if not photo_url:
                name_lower = (item_data.get("name") or "").lower()
                cat_lower = (cat or "").lower()
                
                # Default photo (City / Travel view)
                photo_url = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&auto=format&fit=crop&q=60"
                
                if "restaurant" in name_lower or "food" in name_lower or "bistro" in name_lower or "eatery" in name_lower or "cafe" in name_lower or "café" in name_lower or "dining" in name_lower or cat_lower == "food" or item_data.get("type") == "restaurant":
                    photo_url = "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&auto=format&fit=crop&q=60" # Restaurant / Meal
                elif "temple" in name_lower or "shrine" in name_lower or "church" in name_lower or "mosque" in name_lower or "religious" in cat_lower or "temples" in cat_lower:
                    photo_url = "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&auto=format&fit=crop&q=60" # Temple / Religious
                elif "park" in name_lower or "garden" in name_lower or "nature" in cat_lower or "reserve" in name_lower or "forest" in name_lower or "promenade" in name_lower or "walkway" in name_lower:
                    photo_url = "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&auto=format&fit=crop&q=60" # Nature / Park
                elif "castle" in name_lower or "fort" in name_lower or "palace" in name_lower or "monument" in name_lower or "historical" in cat_lower or "museum" in name_lower or "history" in cat_lower:
                    photo_url = "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800&auto=format&fit=crop&q=60" # Historical / Castle
                elif "market" in name_lower or "shopping" in cat_lower or "bazaar" in name_lower or "plaza" in name_lower or "souvenir" in name_lower:
                    photo_url = "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&auto=format&fit=crop&q=60" # Market / Shopping
                elif "viewpoint" in name_lower or "landmark" in name_lower or "tower" in name_lower or "scenic" in name_lower or "panoramic" in name_lower:
                    photo_url = "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&auto=format&fit=crop&q=60" # Skyline / Tower
                elif "adventure" in cat_lower or "activity" in cat_lower:
                    photo_url = "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=800&auto=format&fit=crop&q=60" # Adventure
                
            # Distance from previous stop
            dist = 0.0
            dur = 0.0
            directions_link = None
            
            if prev_item and prev_item.get("lat") and prev_item.get("lng") and item_lat and item_lng:
                dist = haversine_distance(prev_item["lat"], prev_item["lng"], item_lat, item_lng)
                # Estimate travel duration assuming city driving speed of 30 km/h (dist/30 hours * 60 mins)
                dur = round((dist / 30.0) * 60.0)
                # Generate Google Maps directions link
                directions_link = f"https://www.google.com/maps/dir/?api=1&origin={prev_item['lat']},{prev_item['lng']}&destination={item_lat},{item_lng}"
                
                total_distance_km += dist
                total_duration_mins += dur
                
            if item_lat and item_lng:
                ordered_coords.append((item_lat, item_lng))
                
            # Create a Google Maps location link
            name_query = item_data.get("name") or "Spot"
            if real_place and real_place.get("name"):
                name_query = real_place["name"]
            query_str = f"{name_query}, {trip_in.destination}"
            
            if place_id and not place_id.startswith("dummy_"):
                maps_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}&query_place_id={place_id}"
            else:
                maps_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query_str)}"

            enriched_item = {
                "order": item_data.get("order", idx + 1),
                "type": item_data.get("type", "attraction"),
                "name": item_data.get("name"),
                "description": item_data.get("description"),
                "start_time": item_data.get("start_time"),
                "duration_mins": item_data.get("duration_mins"),
                "estimated_cost": item_data.get("estimated_cost", 0.0),
                "place_id": place_id or (real_place["place_id"] if real_place else None),
                "lat": item_lat,
                "lng": item_lng,
                "rating": item_rating,
                "price_level": real_place.get("price_level") if real_place else None,
                "photo_url": photo_url,
                "address": item_addr,
                "reviews_count": item_reviews,
                "opening_hours": {"descriptions": item_hours} if item_hours else None,
                "entry_fee": item_data.get("estimated_cost", 0.0),
                "best_time_to_visit": item_data.get("best_time_to_visit", "Morning"),
                "category": cat,
                "distance_from_prev": round(dist, 2),
                "duration_from_prev": dur,
                "directions_link": directions_link,
                "google_maps_link": maps_link,
                "arrival_time": item_data.get("start_time"),
                # Calculate departure time roughly
                "departure_time": item_data.get("start_time") # logic handled in frontend or kept same
            }
            
            day_items.append(enriched_item)
            if item_lat and item_lng:
                prev_item = enriched_item
                
        parsed_days.append({
            "day_number": day_data["day_number"],
            "title": day_data.get("title"),
            "items": day_items
        })

    # Generate full route link from ordered coords
    route_link = ""
    if len(ordered_coords) >= 2:
        origin_str = f"{ordered_coords[0][0]},{ordered_coords[0][1]}"
        dest_str = f"{ordered_coords[-1][0]},{ordered_coords[-1][1]}"
        # Intermediate waypoints (max 8)
        way_pts = ordered_coords[1:-1][:8]
        way_str = "|".join([f"{w[0]},{w[1]}" for w in way_pts])
        route_link = f"https://www.google.com/maps/dir/?api=1&origin={origin_str}&destination={dest_str}"
        if way_str:
            route_link += f"&waypoints={way_str}"
            
    # Combine final cost metrics
    raw_metrics = itinerary_data.get("metrics", {})
    metrics = {
        "total_distance_km": round(total_distance_km, 2),
        "total_duration_mins": int(total_duration_mins),
        "transport_cost": raw_metrics.get("transport_cost", 15.0 * num_days),
        "food_cost": raw_metrics.get("food_cost", 50.0 * num_days),
        "ticket_cost": raw_metrics.get("ticket_cost", 10.0 * len(places)),
        "hotel_cost": raw_metrics.get("hotel_cost", 120.0 * (num_days - 1)),
        "total_cost": raw_metrics.get("total_cost", 0.0),
        "remaining_budget": raw_metrics.get("remaining_budget", trip_in.budget),
        "route_link": route_link
    }
    
    # Calculate final total cost just to verify
    metrics["total_cost"] = (
        metrics["transport_cost"] +
        metrics["food_cost"] +
        metrics["ticket_cost"] +
        metrics["hotel_cost"]
    )
    metrics["remaining_budget"] = max(0.0, trip_in.budget - metrics["total_cost"])

    # 5. Save all structured DB Objects
    trip = Trip(
        user_id=user_id,
        destination=trip_in.destination,
        lat=lat,
        lng=lng,
        budget=trip_in.budget,
        currency=trip_in.currency,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        travelers=trip_in.travelers,
        interests=trip_in.interests,
        summary=itinerary_data.get("summary", ""),
        metrics=metrics
    )
    session.add(trip)
    await session.flush()
    
    for day_data in parsed_days:
        day = Day(
            trip_id=trip.id,
            day_number=day_data["day_number"],
            title=day_data.get("title")
        )
        session.add(day)
        await session.flush()
        
        for item_data in day_data.get("items", []):
            item = ItineraryItem(
                day_id=day.id,
                order=item_data["order"],
                type=item_data["type"],
                name=item_data["name"],
                description=item_data["description"],
                start_time=item_data["start_time"],
                duration_mins=item_data["duration_mins"],
                estimated_cost=item_data["estimated_cost"],
                place_id=item_data["place_id"],
                lat=item_data["lat"],
                lng=item_data["lng"],
                rating=item_data["rating"],
                price_level=item_data["price_level"],
                photo_url=item_data["photo_url"],
                address=item_data["address"],
                reviews_count=item_data["reviews_count"],
                opening_hours=item_data["opening_hours"],
                entry_fee=item_data["entry_fee"],
                best_time_to_visit=item_data["best_time_to_visit"],
                category=item_data["category"],
                distance_from_prev=item_data["distance_from_prev"],
                duration_from_prev=item_data["duration_from_prev"],
                directions_link=item_data["directions_link"],
                google_maps_link=item_data["google_maps_link"],
                arrival_time=item_data["arrival_time"],
                departure_time=item_data["departure_time"]
            )
            session.add(item)
            
    await session.commit()
    await session.refresh(trip)
    return trip

