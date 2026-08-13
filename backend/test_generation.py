import asyncio
import httpx
import json
import sys

# Reconfigure stdout to support unicode prints on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def test_trip_generation():
    print("Testing full trip generation backend endpoint...")
    base_url = "http://localhost:8000/api/v1"
    
    # 1. Register a dummy user
    register_url = f"{base_url}/auth/register"
    email = f"test_user_{asyncio.get_event_loop().time()}@example.com"
    payload = {
        "email": email,
        "name": "Test User",
        "password": "testpassword123"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            reg_resp = await client.post(register_url, json=payload)
            print(f"Registration Status: {reg_resp.status_code}")
            
            # 2. Login
            login_url = f"{base_url}/auth/login"
            fd = {
                "username": email,
                "password": "testpassword123"
            }
            log_resp = await client.post(login_url, data=fd)
            print(f"Login Status: {log_resp.status_code}")
            token = log_resp.json().get("access_token")
            print(f"Token: {token[:15]}...")
            
            # 3. Create Trip
            create_trip_url = f"{base_url}/trips/"
            trip_payload = {
                "destination": "Kyoto",
                "budget": 2000.0,
                "currency": "USD",
                "start_date": "2026-09-01T00:00:00Z",
                "end_date": "2026-09-03T00:00:00Z",
                "travelers": 2,
                "interests": ["Temples & holy places"]
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            print("Sending request to generate Kyoto trip (Kyoto temples). This will fetch real Google Maps places, run TSP optimization, and prompt OpenAI LLaMA...")
            trip_resp = await client.post(create_trip_url, json=trip_payload, headers=headers, timeout=120.0)
            print(f"Trip Creation Status: {trip_resp.status_code}")
            
            if trip_resp.status_code == 200:
                trip_data = trip_resp.json()
                print("\nSUCCESS! Generated Trip Details:")
                print(f"Destination: {trip_data['destination']}")
                print(f"Summary: {trip_data['summary']}")
                print(f"Total Distance: {trip_data['metrics']['total_distance_km']} km")
                print(f"Total Travel Time: {trip_data['metrics']['total_duration_mins']} mins")
                print(f"Total Cost: {trip_data['metrics']['total_cost']} USD")
                print(f"Remaining Budget: {trip_data['metrics']['remaining_budget']} USD")
                print(f"Route Link: {trip_data['metrics']['route_link']}")
                
                print("\nFirst Day Itinerary:")
                if trip_data.get("days"):
                    day = trip_data["days"][0]
                    print(f"Day {day['day_number']}: {day['title']}")
                    for item in day.get("items", []):
                        print(f"  [{item['start_time']}] {item['name']} ({item['category']}) - {item['description'][:60]}...")
                        if item.get("distance_from_prev"):
                            print(f"     -> Travel: {item['distance_from_prev']} km, {item['duration_from_prev']} mins")
            else:
                print(f"Failed: {trip_resp.text}")
                
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_trip_generation())
