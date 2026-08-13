from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# Find the project backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Meridian API"
    DATABASE_PATH: Path = BACKEND_DIR / "trip_planner.db"
    DATABASE_URL: str = ""
    SECRET_KEY: str = "PLEASE_CHANGE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env")

    def model_post_init(self, __context):
        # If DATABASE_URL is provided in env (e.g. from Supabase/Neon), use it
        if self.DATABASE_URL:
            # Handle standard postgres/postgresql scheme and convert to asyncpg
            if self.DATABASE_URL.startswith("postgres://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
            elif self.DATABASE_URL.startswith("postgresql://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            # Fallback to local SQLite database
            self.DATABASE_URL = f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

@lru_cache()
def get_settings():
    return Settings()

