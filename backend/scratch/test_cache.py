import asyncio
import sys
import os

# Add parent directories to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cache_service import get_cache, set_cache

async def test():
    print("Testing cache_service...")
    key = "test_key_123"
    value = {"message": "hello from cache!"}
    
    # Write to cache
    await set_cache(key, value)
    print("Saved to cache.")
    
    # Read from cache
    retrieved = await get_cache(key)
    print("Retrieved from cache:", retrieved)
    
    if retrieved == value:
        print("SUCCESS: Cache works perfectly!")
    else:
        print("FAILURE: Cache mismatch!")

if __name__ == "__main__":
    asyncio.run(test())
