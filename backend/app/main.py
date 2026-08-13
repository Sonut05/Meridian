from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.router import api_router
from app.db.database import engine
from app.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Set up CORS for the Next.js/HTML frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}

