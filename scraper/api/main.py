"""FastAPI application - REST API for scraper-pro."""

from fastapi import FastAPI

from scraper.api.routes.contacts import router as contacts_router
from scraper.api.routes.scraping import router as scraping_router
from scraper.api.routes.campaigns import router as campaigns_router

app = FastAPI(
    title="Scraper-Pro API",
    description="Scraping + Email pipeline API for SOS-Expat & Ulixai",
    version="1.0.0",
)

app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(scraping_router, prefix="/api/v1/scraping", tags=["scraping"])
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scraper-pro"}
