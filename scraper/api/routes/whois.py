"""API routes for WHOIS domain lookup."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from scraper.api.auth import verify_hmac
from scraper.api.schemas import WhoisLookupRequest
from scraper.database import get_db_session
from scraper.modules.whois_lookup import lookup_whois

router = APIRouter()


@router.post("/lookup", dependencies=[Depends(verify_hmac)])
async def whois_lookup(payload: WhoisLookupRequest):
    """Perform WHOIS lookup for a domain."""
    domain = payload.domain.strip().lower()

    if "." not in domain:
        raise HTTPException(status_code=400, detail="Invalid domain format")

    result = lookup_whois(domain)
    return result


@router.get("/history", dependencies=[Depends(verify_hmac)])
async def whois_history():
    """Return the 50 most recent WHOIS lookups from cache."""
    with get_db_session() as session:
        rows = session.execute(
            text("""
                SELECT domain, registrar, whois_private, cloudflare_protected,
                       registrant_name, registrant_org, registrant_country,
                       lookup_status, creation_date, expiration_date, looked_up_at
                FROM whois_cache
                ORDER BY looked_up_at DESC
                LIMIT 50
            """)
        ).mappings().all()

    return {"lookups": [dict(r) for r in rows]}
