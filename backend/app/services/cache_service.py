import json
import os
import tempfile
import aiosqlite
from app.core.config import get_settings

settings = get_settings()

# If running on Netlify/Serverless or using a remote database, place SQLite cache in a writeable /tmp path
if "NETLIFY" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ or not settings.DATABASE_URL.startswith("sqlite"):
    DB_PATH = os.path.join(tempfile.gettempdir(), "trip_planner_cache.db")
else:
    DB_PATH = str(settings.DATABASE_PATH)

async def init_cache():
    """Initializes the api_cache table if it does not exist."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    except Exception as e:
        print(f"Error initializing database cache table: {e}")

async def get_cache(key: str, max_age_seconds: int = None) -> dict | None:
    """Retrieves a cached JSON response as a dictionary, or returns None if not found.
    Optionally filters by maximum age in seconds."""
    try:
        await init_cache()  # ensure table exists
        async with aiosqlite.connect(DB_PATH) as db:
            if max_age_seconds is not None:
                query = "SELECT value FROM api_cache WHERE key = ? AND (strftime('%s', 'now') - strftime('%s', created_at)) < ?"
                params = (key, max_age_seconds)
            else:
                query = "SELECT value FROM api_cache WHERE key = ?"
                params = (key,)
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
    except Exception as e:
        print(f"Error reading cache for key '{key}': {e}")
    return None

async def set_cache(key: str, value: dict):
    """Saves a JSON-serializable dictionary into the cache database."""
    try:
        await init_cache()  # ensure table exists
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO api_cache (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )
            await db.commit()
    except Exception as e:
        print(f"Error writing cache for key '{key}': {e}")
