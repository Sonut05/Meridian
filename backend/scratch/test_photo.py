import asyncio
import httpx

async def test_photos():
    print("Testing Places API search with photos...")
    RAPIDAPI_KEY = "d178086224msh15da67ef876680dp1bcec6jsncd75355e1e65"
    url = "https://google-map-places-new-v2.p.rapidapi.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos",
        "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    payload = {
        "textQuery": "Eiffel Tower"
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            places = data.get("places", [])
            if not places:
                print("No places found.")
                return
            
            place = places[0]
            print(f"Name: {place.get('displayName', {}).get('text')}")
            photos = place.get("photos", [])
            print(f"Photos count: {len(photos)}")
            if not photos:
                print("No photos found in Eiffel Tower search.")
                return
            
            photo_name = photos[0].get("name")
            print(f"First photo name: {photo_name}")
            
            # Now let's try to fetch this photo media!
            photo_url = f"https://google-map-places-new-v2.p.rapidapi.com/v1/{photo_name}/media"
            print(f"Fetching photo media from: {photo_url}")
            photo_resp = await client.get(
                photo_url,
                headers={
                    "x-rapidapi-host": "google-map-places-new-v2.p.rapidapi.com",
                    "x-rapidapi-key": RAPIDAPI_KEY
                },
                params={"maxWidthPx": 400},
                follow_redirects=False
            )
            print(f"Photo status (no redirect): {photo_resp.status_code}")
            redirect_url = photo_resp.headers.get("Location")
            print(f"Redirect Location: {redirect_url}")
            
            if redirect_url:
                print("Fetching redirect URL without any headers...")
                redirect_resp = await client.get(redirect_url)
                print(f"Redirect fetch status: {redirect_resp.status_code}")
                print(f"Redirect fetch content length: {len(redirect_resp.content)}")
                print(f"Content-Type: {redirect_resp.headers.get('Content-Type')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_photos())
