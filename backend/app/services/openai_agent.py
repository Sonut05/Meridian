import json
import httpx
import hashlib
from app.core.config import get_settings
from app.services.cache_service import get_cache, set_cache

settings = get_settings()

async def generate_itinerary(
    destination: str,
    num_days: int,
    budget: float,
    currency: str,
    travelers: int,
    interests: list[str],
    places: list[dict]
) -> dict:
    """Uses LLM to distribute real-world places into a structured day-by-day itinerary
    respecting budget, categories, opening hours, and calculating overall costs."""
    
    # 1. Check cache first
    try:
        key_dict = {
            "destination": destination.lower().strip(),
            "num_days": num_days,
            "budget": budget,
            "currency": currency,
            "travelers": travelers,
            "interests": sorted(interests),
            "places": [{"place_id": p.get("place_id"), "name": p.get("name")} for p in places]
        }
        key_str = json.dumps(key_dict, sort_keys=True)
        cache_key = f"itinerary:{hashlib.sha256(key_str.encode()).hexdigest()}"
        
        cached = await get_cache(cache_key)
        if cached:
            return cached
    except Exception as e:
        print(f"Error checking itinerary cache: {e}")
        cache_key = None

    def get_offline_fallback(reason: str = "No API key"):
        used_names = set()
        
        # Separate candidate places into attractions and restaurants
        candidate_restaurants = []
        candidate_attractions = []
        
        restaurant_types = {"restaurant", "cafe", "food", "bar", "bakery", "meal_takeaway", "meal_delivery", "eating_establishment"}
        
        if places:
            for p in places:
                p_types = set(p.get("types", []))
                if p_types.intersection(restaurant_types):
                    candidate_restaurants.append(p)
                else:
                    candidate_attractions.append(p)

        generic_attractions = [
            "Scenic Landmark",
            "Botanical Garden",
            "Historic Castle",
            "Museum of Art",
            "Cultural Heritage Center",
            "Local Market Plaza",
            "Panoramic Viewpoint",
            "Traditional Temple",
            "Riverside Promenade",
            "Architectural Wonder",
            "Old Town District",
            "Artisan Craft Village",
            "Royal Palace Grounds",
            "Peace Memorial Park",
            "Nature Reserve Trail"
        ]

        generic_restaurants = [
            "Traditional Restaurant",
            "Popular Local Eatery",
            "Cozy Bistro Cafe",
            "Famous Dining Spot",
            "Authentic Food House",
            "Riverside Cafe Bistro",
            "Gourmet Kitchen Diner",
            "Classic Bar Grill",
            "Premium Steakhouse",
            "Local Culinary Place"
        ]

        dummy_days = []
        for d in range(1, num_days + 1):
            items = []
            
            # 1. Morning attraction
            p1 = None
            if candidate_attractions:
                for p in candidate_attractions:
                    p_name = p.get("name")
                    if p_name and p_name not in used_names:
                        p1 = p
                        used_names.add(p_name)
                        break
            
            if not p1:
                gen_name = generic_attractions[((d - 1) * 2) % len(generic_attractions)]
                p_name = f"Historic {gen_name} of {destination}"
                p1 = {
                    "name": p_name,
                    "place_id": f"dummy_site_{d}_1",
                    "lat": 0.0,
                    "lng": 0.0,
                    "category": "Historical"
                }

            items.append({
                "order": 1,
                "type": "attraction",
                "name": p1.get("name"),
                "description": f"Explore the beautiful and historic landmarks of {destination}, taking in the rich heritage and culture.",
                "start_time": "09:30",
                "duration_mins": 120,
                "estimated_cost": 15.0,
                "category": p1.get("category", "Historical"),
                "best_time_to_visit": "Morning",
                "place_id": p1.get("place_id")
            })
            
            # 2. Lunch restaurant
            p_lunch = None
            if candidate_restaurants:
                for p in candidate_restaurants:
                    p_name = p.get("name")
                    if p_name and p_name not in used_names:
                        p_lunch = p
                        used_names.add(p_name)
                        break
            
            if not p_lunch:
                gen_rest = generic_restaurants[((d - 1) * 2) % len(generic_restaurants)]
                p_name = f"{gen_rest} of {destination}"
                p_lunch = {
                    "name": p_name,
                    "place_id": f"dummy_lunch_{d}",
                    "lat": 0.0,
                    "lng": 0.0,
                    "category": "Food"
                }

            items.append({
                "order": 2,
                "type": "restaurant",
                "name": p_lunch.get("name"),
                "description": f"Enjoy local specialties and authentic cuisine of {destination} for lunch in a cozy atmosphere.",
                "start_time": "12:00",
                "duration_mins": 60,
                "estimated_cost": 20.0,
                "category": "Food",
                "best_time_to_visit": "Noon",
                "place_id": p_lunch.get("place_id")
            })
            
            # 3. Afternoon attraction
            p2 = None
            if candidate_attractions:
                for p in candidate_attractions:
                    p_name = p.get("name")
                    if p_name and p_name not in used_names:
                        p2 = p
                        used_names.add(p_name)
                        break
            
            if not p2:
                gen_name = generic_attractions[((d - 1) * 2 + 1) % len(generic_attractions)]
                p_name = f"Scenic {gen_name} of {destination}"
                p2 = {
                    "name": p_name,
                    "place_id": f"dummy_park_{d}_2",
                    "lat": 0.0,
                    "lng": 0.0,
                    "category": "Nature"
                }

            items.append({
                "order": 3,
                "type": "attraction",
                "name": p2.get("name"),
                "description": f"Take a relaxing stroll and enjoy the scenic views and nature at the local parks of {destination}.",
                "start_time": "13:30",
                "duration_mins": 90,
                "estimated_cost": 0.0,
                "category": p2.get("category", "Nature"),
                "best_time_to_visit": "Afternoon",
                "place_id": p2.get("place_id")
            })

            # 4. Dinner restaurant
            p_dinner = None
            if candidate_restaurants:
                for p in candidate_restaurants:
                    p_name = p.get("name")
                    if p_name and p_name not in used_names:
                        p_dinner = p
                        used_names.add(p_name)
                        break
            
            if not p_dinner:
                gen_rest = generic_restaurants[((d - 1) * 2 + 1) % len(generic_restaurants)]
                p_name = f"{gen_rest} of {destination}"
                p_dinner = {
                    "name": p_name,
                    "place_id": f"dummy_dinner_{d}",
                    "lat": 0.0,
                    "lng": 0.0,
                    "category": "Food"
                }

            items.append({
                "order": 4,
                "type": "restaurant",
                "name": p_dinner.get("name"),
                "description": f"Unwind and savor a premium dinner experience in the heart of {destination}.",
                "start_time": "18:00",
                "duration_mins": 90,
                "estimated_cost": 35.0,
                "category": "Food",
                "best_time_to_visit": "Evening",
                "place_id": p_dinner.get("place_id")
            })

            dummy_days.append({
                "day_number": d,
                "title": f"Explore {destination} - Day {d}",
                "items": items
            })

        # Calculate metrics
        food_cost = 55.0 * travelers * num_days
        ticket_cost = 15.0 * travelers * num_days
        transport_cost = 20.0 * num_days
        hotel_cost = 120.0 * (num_days - 1)
        total_cost = food_cost + ticket_cost + transport_cost + hotel_cost

        return {
            "summary": f"Itinerary for {destination} ({reason})",
            "days": dummy_days,
            "metrics": {
                "transport_cost": transport_cost,
                "food_cost": food_cost,
                "ticket_cost": ticket_cost,
                "hotel_cost": hotel_cost,
                "total_cost": total_cost,
                "remaining_budget": max(0.0, budget - total_cost)
            }
        }

    if not settings.OPENAI_API_KEY:
        return get_offline_fallback()

    # Format real places for prompt
    places_str = ""
    for idx, p in enumerate(places):
        places_str += f"""
Index: {idx}
Name: {p['name']}
Place ID: {p['place_id']}
Location: Lat {p['lat']}, Lng {p['lng']}
Rating: {p['rating']} ({p['reviews_count']} reviews)
Types: {', '.join(p['types'])}
Opening Hours: {', '.join(p['opening_hours']) if p['opening_hours'] else 'Not Available'}
"""

    prompt = f"""
Create a detailed {num_days}-day itinerary for {travelers} travelers visiting {destination}.
The total budget for this trip (excluding flights) is {budget} {currency}.
Their main interests are: {', '.join(interests)}.

You MUST use ONLY the following real-world candidate places from Google Maps to build the attractions list.
Do NOT hallucinate any attraction places outside this list. Keep the places generally in the order they are listed below, as they are already geographically optimized to avoid backtracking.

Candidate Places:
{places_str}

Instructions:
1. Distribute these places across the {num_days} days.
2. Group nearby attractions on the same day.
3. Do NOT repeat any candidate place in the itinerary. Each place from the candidate list should be scheduled at most ONCE during the entire trip.
4. For each day, include:
   - A title
   - Itinerary items in order. Each item must have:
     - "name": Must exactly match one of the candidate names, or a generic placeholder (like "Breakfast", "Lunch", "Dinner", "Hotel Check-in", "Travel to next city" etc.)
     - "type": "attraction" | "restaurant" | "activity" | "transport"
     - "description": Rich, detailed description of what to do there.
     - "start_time": Format HH:MM (e.g. "09:00", "13:30")
     - "duration_mins": Integer duration of visit (e.g., 90, 120)
     - "estimated_cost": Estimate the actual, correct entry fee/ticket price (for attractions) or average meal cost (for restaurants) in the destination's local currency. Research your knowledge base thoroughly to ensure these prices are accurate and match current rates. If an attraction is free, set it to 0.0.
     - "category": e.g. "Historical", "Nature", "Adventure", "Shopping", "Food", "Relaxation", "Religious"
     - "best_time_to_visit": Short string recommendation (e.g. "Morning", "Sunset", "Afternoon")
     - "place_id": String (Must match the exact Google Place ID from the candidate list, or null if it's a generic item like breakfast/hotel/transport)
5. Calculate cost metrics for the entire trip:
   - "transport_cost": total transportation cost (taxis, public transit)
   - "food_cost": total estimated food expenses for all travelers
   - "ticket_cost": total admission/ticket costs for all attractions
   - "hotel_cost": total lodging expenses (set 0.0 if not applicable)
   - "total_cost": sum of transport, food, ticket, and hotel costs
   - "remaining_budget": budget - total_cost

Return ONLY valid JSON matching this schema:
{{
  "summary": "trip summary",
  "days": [
    {{
      "day_number": 1,
      "title": "Day Title",
      "items": [
        {{
          "order": 1,
          "type": "attraction",
          "name": "Exact Name from Candidate List",
          "description": "description",
          "start_time": "09:00",
          "duration_mins": 120,
          "estimated_cost": 15.0,
          "category": "Historical",
          "best_time_to_visit": "Morning",
          "place_id": "Place ID string or null"
        }}
      ]
    }}
  ],
  "metrics": {{
    "transport_cost": 45.0,
    "food_cost": 150.0,
    "ticket_cost": 60.0,
    "hotel_cost": 300.0,
    "total_cost": 555.0,
    "remaining_budget": 1245.0
  }}
}}
"""

    # Detect standard OpenAI key vs RapidAPI key
    is_standard_openai = settings.OPENAI_API_KEY.startswith("sk-")
    
    if not is_standard_openai:
        print("💡 RECOMMENDATION: The configured OpenAI API key is a RapidAPI proxy key which has limited monthly quotas (often returning HTTP 429).")
        print("   To avoid rate limits and get 100% accurate results, update your .env to use an official OpenAI key starting with 'sk-'.")
    
    if is_standard_openai:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
    else:
        url = "https://open-ai21.p.rapidapi.com/conversationllama"
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": "open-ai21.p.rapidapi.com",
            "x-rapidapi-key": settings.OPENAI_API_KEY
        }
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "web_access": False
        }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"LLM API returned status code {response.status_code}: {response.text}")
                return get_offline_fallback(reason=f"LLM status {response.status_code}")
                
            data = response.json()
            if is_standard_openai:
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            else:
                content = data.get("result", data.get("response", str(data)) or str(data))
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            res = json.loads(content.strip(), strict=False)
            if cache_key and res and "days" in res:
                await set_cache(cache_key, res)
            return res
    except Exception as e:
        print(f"Error calling LLM or parsing JSON: {e}")
        return get_offline_fallback(reason=f"API Error: {str(e)}")
