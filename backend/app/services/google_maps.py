import httpx
import asyncio
from app.core.config import get_settings
from app.services.cache_service import get_cache, set_cache

settings = get_settings()

async def get_coordinates(destination: str) -> tuple[float, float]:
    """Returns lat, lng for a destination using RapidAPI Google Maps Places V2."""
    dest_clean = destination.lower().strip()
    cache_key = f"coords:{dest_clean}"
    cached = await get_cache(cache_key)
    if cached and "lat" in cached and "lng" in cached:
        return cached["lat"], cached["lng"]

    if not settings.GOOGLE_MAPS_API_KEY:
        return (40.7128, -74.0060)

    url = "https://google-map-places-new-v2.p.rapidapi.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.location",
        "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
        "x-rapidapi-key": settings.GOOGLE_MAPS_API_KEY
    }
    payload = {
        "textQuery": destination
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
            data = resp.json()
            if data.get("places"):
                loc = data["places"][0]["location"]
                lat, lng = loc["latitude"], loc["longitude"]
                await set_cache(cache_key, {"lat": lat, "lng": lng})
                return lat, lng
    except Exception as e:
        print(f"Error in get_coordinates: {e}")
    return (0.0, 0.0)

async def _fetch_query(client: httpx.AsyncClient, query: str) -> list[dict]:
    url = "https://google-map-places-new-v2.p.rapidapi.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.regularOpeningHours,places.types,places.priceLevel,places.photos",
        "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
        "x-rapidapi-key": settings.GOOGLE_MAPS_API_KEY
    }
    payload = {
        "textQuery": query,
        "languageCode": "en"
    }
    try:
        resp = await client.post(url, headers=headers, json=payload, timeout=20.0)
        if resp.status_code == 200:
            return resp.json().get("places", [])
    except Exception as e:
        print(f"Error fetching query '{query}': {e}")
    return []

async def resolve_photo_url(client: httpx.AsyncClient, photo_name: str) -> str | None:
    """Resolves a public redirect URL for a photo from RapidAPI and caches it."""
    if not photo_name:
        return None
    cache_key = f"photo_url:{photo_name}"
    cached = await get_cache(cache_key, max_age_seconds=86400)
    if cached and isinstance(cached, dict) and "url" in cached:
        return cached["url"]

    url = f"https://google-map-places-new-v2.p.rapidapi.com/v1/{photo_name}/media"
    try:
        resp = await client.get(
            url,
            headers={
                "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
                "x-rapidapi-key": settings.GOOGLE_MAPS_API_KEY
            },
            params={"maxWidthPx": 400},
            follow_redirects=True,
            timeout=15.0
        )
        if resp.status_code == 200:
            final_url = str(resp.url)
            if "googleusercontent.com" in final_url or "google.com" in final_url:
                await set_cache(cache_key, {"url": final_url})
                return final_url
    except Exception as e:
        print(f"Error resolving photo {photo_name}: {e}")
    return None

async def search_popular_places(destination: str, interests: list[str]) -> list[dict]:
    """Search for popular spots in destination matching the interests using Places V2 API."""
    dest_clean = destination.lower().strip()
    interests_str = ",".join(sorted(interests))
    cache_key = f"popular_places:{dest_clean}:{interests_str.lower()}"
    
    cached = await get_cache(cache_key)
    if cached and isinstance(cached, list):
        return cached

    if not settings.GOOGLE_MAPS_API_KEY:
        # Fallback dummy data if no key
        return []

    # Form queries based on interests
    queries = []
    
    # 1. Main attractions query
    queries.append(f"top tourist attractions in {destination}")
    # 2. Main restaurants query
    queries.append(f"best restaurants and cafes in {destination}")
    
    # 3. Specific interest queries
    interest_queries = {
        "Temples & holy places": f"temples and shrines in {destination}",
        "Food & drink": f"top rated restaurants and food spots in {destination}",
        "History & culture": f"museums and historical sights in {destination}",
        "Nature & outdoors": f"parks and gardens in {destination}",
        "Art & design": f"art galleries and museums in {destination}",
        "Nightlife": f"bars and clubs in {destination}",
        "Markets & shopping": f"markets and shopping malls in {destination}"
    }
    
    for interest in interests:
        if interest in interest_queries:
            # Skip if we already added restaurants query
            if interest == "Food & drink":
                continue
            queries.append(interest_queries[interest])
            
    # Max 3 queries to keep it fast
    queries = queries[:3]
    
    places_temp = []
    seen_ids = set()
    
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_query(client, q) for q in queries]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            for p in result:
                p_id = p.get("id")
                if p_id and p_id not in seen_ids:
                    seen_ids.add(p_id)
                    # Normalize structure
                    display_name = p.get("displayName", {}).get("text", "Unknown Spot")
                    location = p.get("location", {})
                    lat = location.get("latitude")
                    lng = location.get("longitude")
                    
                    if lat and lng:
                        photo_name = None
                        photos = p.get("photos", [])
                        if photos:
                            photo_name = photos[0].get("name")
                            
                        places_temp.append({
                            "place_id": p_id,
                            "name": display_name,
                            "address": p.get("formattedAddress"),
                            "lat": lat,
                            "lng": lng,
                            "rating": p.get("rating", 4.0),
                            "reviews_count": p.get("userRatingCount", 0),
                            "types": p.get("types", []),
                            "price_level": p.get("priceLevel"),
                            "opening_hours": p.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
                            "photo_name": photo_name,
                            "photo_url": None
                        })
                        
        import urllib.parse
        # Set proxy URL directly to avoid slow on-the-fly resolution during generation
        for p in places_temp:
            if p["photo_name"]:
                p["photo_url"] = f"/api/v1/trips/photo?photo_name={urllib.parse.quote(p['photo_name'])}"
            del p["photo_name"]
        places = places_temp
                        
    if places:
        await set_cache(cache_key, places)
    return places

async def search_places(query: str, location: tuple[float, float] = None, radius: int = 50000) -> list[dict]:
    return []

async def fetch_place_details(name: str, destination: str) -> dict | None:
    """Fetches details (lat, lng, rating, reviews_count, photo_url, address, opening_hours)
    for a place name within a destination using RapidAPI Google Maps Places V2."""
    name_clean = name.lower().strip()
    dest_clean = destination.lower().strip()
    
    # Avoid searching for generic placeholders
    generic_placeholders = [
        "breakfast", "lunch", "dinner", "brunch", "cafe", "café", "restaurant",
        "coffee", "food", "meal", "drink", "snack", "bar", "pub", "club",
        "hotel", "check-in", "check-out", "lodging", "accommodation",
        "airport", "station", "train", "bus", "subway", "taxi", "transit",
        "travel to", "flight", "walk", "stroll", "free time", "leisure",
        "relaxation", "explore", "sightseeing", "workshop", "activity",
        "souvenir", "shopping", "rest", "local place", "local spot", "spot", "place"
    ]
    if any(placeholder in name_clean for placeholder in generic_placeholders) and len(name) < 30:
        return None

    cache_key = f"place_details:{name_clean}:{dest_clean}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    if not settings.GOOGLE_MAPS_API_KEY:
        return None

    query = f"{name}, {destination}"
    url = "https://google-map-places-new-v2.p.rapidapi.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.regularOpeningHours,places.types,places.priceLevel,places.photos",
        "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
        "x-rapidapi-key": settings.GOOGLE_MAPS_API_KEY
    }
    payload = {
        "textQuery": query,
        "languageCode": "en"
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
            if resp.status_code == 200:
                places = resp.json().get("places", [])
                if places:
                    p = places[0]
                    p_id = p.get("id")
                    display_name = p.get("displayName", {}).get("text", name)
                    location = p.get("location", {})
                    lat = location.get("latitude")
                    lng = location.get("longitude")
                    
                    photo_url = None
                    photos = p.get("photos", [])
                    if photos:
                        photo_name = photos[0].get("name")
                        import urllib.parse
                        photo_url = f"/api/v1/trips/photo?photo_name={urllib.parse.quote(photo_name)}"
                            
                    res = {
                        "place_id": p_id,
                        "name": display_name,
                        "address": p.get("formattedAddress"),
                        "lat": lat,
                        "lng": lng,
                        "rating": p.get("rating"),
                        "reviews_count": p.get("userRatingCount", 0),
                        "types": p.get("types", []),
                        "price_level": p.get("priceLevel"),
                        "opening_hours": p.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
                        "photo_url": photo_url
                    }
                    await set_cache(cache_key, res)
                    return res
    except Exception as e:
        print(f"Error fetching details for '{query}': {e}")
    return None

