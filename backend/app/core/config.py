from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Meridian API"
    DATABASE_URL: str = "sqlite+aiosqlite:///./trip_planner.db"
    SECRET_KEY: str = "PLEASE_CHANGE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
