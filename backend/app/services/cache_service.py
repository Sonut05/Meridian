import json
from sqlalchemy import text
from app.db.database import engine

async def init_cache():
    """Initializes the api_cache table if it does not exist."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
    except Exception as e:
        print(f"Error initializing database cache table: {e}")

async def get_cache(key: str, max_age_seconds: int = None) -> dict | None:
    """Retrieves a cached JSON response as a dictionary, or returns None if not found.
    Optionally filters by maximum age in seconds."""
    try:
        await init_cache()  # ensure table exists
        async with engine.connect() as conn:
            if max_age_seconds is not None:
                # Postgres syntax for interval comparison
                query = text("""
                    SELECT value FROM api_cache 
                    WHERE key = :key AND (EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - EXTRACT(EPOCH FROM created_at)) < :max_age
                """)
                params = {"key": key, "max_age": max_age_seconds}
            else:
                query = text("SELECT value FROM api_cache WHERE key = :key")
                params = {"key": key}
                
            result = await conn.execute(query, params)
            row = result.fetchone()
            if row:
                return json.loads(row[0])
    except Exception as e:
        print(f"Error reading cache for key '{key}': {e}")
    return None

async def set_cache(key: str, value: dict):
    """Saves a JSON-serializable dictionary into the cache database."""
    try:
        await init_cache()  # ensure table exists
        async with engine.begin() as conn:
            # Postgres UPSERT syntax
            await conn.execute(text("""
                INSERT INTO api_cache (key, value) VALUES (:key, :value)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, created_at = CURRENT_TIMESTAMP
            """), {"key": key, "value": json.dumps(value)})
    except Exception as e:
        print(f"Error writing cache for key '{key}': {e}")
