import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_v1_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("studio.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Fresh Local AI Content Studio Database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully (SQLite WAL).")

    yield

    logger.info("Shutting down API server...")
    await engine.dispose()
    logger.info("Database connection closed.")


app = FastAPI(
    title="Fresh Local AI Content Studio API",
    version="0.1.0",
    description="Local-first, single-niche, engine-based content production backend.",
    lifespan=lifespan,
)

# CORS configuration restricted to local web origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint and V1 routers
app.include_router(health_router)
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": "Fresh Local AI Content Studio API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "status": "running",
    }
