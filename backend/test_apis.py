import asyncio
import os
import httpx
import json
from pathlib import Path

# Load env file if it exists
if os.path.exists(Path(__file__).parent / ".env"):
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

RAPIDAPI_KEY = os.getenv("OPENAI_API_KEY", "")

async def test_openai():
    print("Testing OpenAI RapidAPI...")
    url = "https://open-ai21.p.rapidapi.com/conversationllama"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "open-ai21.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    payload = {
        "messages": [
            {"role": "user", "content": "Return the word 'HELLO' in JSON format like {\"word\": \"HELLO\"}"}
        ],
        "web_access": False
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

async def test_google_maps():
    print("\nTesting Google Maps RapidAPI...")
    url = "https://google-map-places-new-v2.p.rapidapi.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.location",
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
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
    asyncio.run(test_google_maps())
