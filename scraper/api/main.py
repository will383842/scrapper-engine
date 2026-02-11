"""FastAPI application - REST API for scraper-pro."""

import logging
import os

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scraper.api.routes.contacts import router as contacts_router
from scraper.api.routes.scraping import router as scraping_router
from scraper.api.routes.campaigns import router as campaigns_router
from scraper.api.routes.whois import router as whois_router
from scraper.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Scraper-Pro API",
    description="Scraping + Email pipeline API for SOS-Expat & Ulixai",
    version="1.0.0",
)

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(scraping_router, prefix="/api/v1/scraping", tags=["scraping"])
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(whois_router, prefix="/api/v1/whois", tags=["whois"])


def _check_postgres() -> bool:
    """Check PostgreSQL connectivity."""
    try:
        from scraper.database import get_db_session
        from sqlalchemy import text
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False


def _check_redis() -> bool:
    """Check Redis connectivity."""
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            socket_connect_timeout=3,
        )
        return r.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


@app.get("/health")
async def health():
    pg = _check_postgres()
    rd = _check_redis()
    status = "ok" if (pg and rd) else "degraded"
    return {
        "status": status,
        "service": "scraper-pro",
        "postgres": pg,
        "redis": rd,
    }
